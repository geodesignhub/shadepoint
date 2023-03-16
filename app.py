#!/usr/bin/env python3
from flask import Flask, url_for
from flask import render_template
from flask import request, Response
import json, GeodesignHub
import config
from dataclasses import dataclass, asdict
from dacite import from_dict
from typing import List
from geojson import Feature, FeatureCollection, Polygon, LineString
from data_definitions import ErrorResponse, DiagramShadowSuccessResponse, GeodesignhubProjectBounds, GeodesignhubSystem, GeodesignhubProjectData, GeodesignhubDiagramDetailShadow, GeodesignhubDiagramProperties
from conn import get_redis
import os

redis = get_redis()

from rq import Queue
from worker import conn

q = Queue(connection=conn)

app = Flask(__name__)

@app.route('/', methods = ['GET'])
def home():
	return render_template('home.html')

@app.route('/diagram_shadow', methods = ['GET'])
def diagram_shadow():
	''' This is the root of the webservice, upon successful authentication a text will be displayed in the browser '''
	try:
		projectid = request.args.get('projectid')
		apitoken = request.args.get('apitoken')
		diagramid = request.args.get('diagramid')

	except KeyError as e:
		error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
		return Response(asdict(error_msg), status=400, mimetype='application/json')

	if projectid and diagramid and apitoken:
		# Initialize the API
		myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=projectid, token=apitoken)
		# Download Data		
		s = myAPIHelper.get_systems()
		b = myAPIHelper.get_project_bounds()
		d = myAPIHelper.get_diagrams()
		
		# Check responses / data
		try:
			assert s.status_code == 200
		except AssertionError as ae:			
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')
		
		systems = s.json()
		all_systems: List[GeodesignhubSystem] = []
		for s in systems:
			current_system = from_dict(data_class = GeodesignhubSystem, data = s)
			all_systems.append(current_system)
			
		try:
			assert d.status_code == 200
		except AssertionError as ae:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')

		_diagram_details_raw = d.json()

		_diagram_details_feature_collection = _diagram_details_raw['geojson']
		_all_features: List[Feature] = []
		for f in _diagram_details_feature_collection:
			# We assume that GDH will provide a polygon
			if f['geometry']['type'] == 'Polygon':					
				_geometry = Polygon(coordinates=f['geometry']['coordinates'])
			elif f['geometry']['type'] == 'LineString':
				_geometry = LineString(coordinates=f['geometry']['coordinates'])
			else: 
				error_msg = ErrorResponse(status=0, message="Building shadows can only be computed for polygon features, you are trying to compute shadows for .",code=400)
				return Response(asdict(error_msg), status=400, mimetype='application/json')
			_feature = Feature(geometry=_geometry, properties={})
			_all_features.append(_feature)

		_diagram_feature_collection = FeatureCollection(features=_all_features)
		_diagram_properties = from_dict(data_class = GeodesignhubDiagramProperties, data = _diagram_details_raw)
		diagram_data = GeodesignhubDiagramDetailShadow(geojson=_diagram_feature_collection, properties=_diagram_properties)


		try:
			assert b.status_code == 200
		except AssertionError as ae:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')

		bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())			
		project_data = GeodesignhubProjectData(systems=all_systems ,bounds=bounds)		
		

		success_response = DiagramShadowSuccessResponse(status=1,message="Data from Geodesignhub retrieved",diagram_data=diagram_data, project_data = project_data)
		
		return render_template('diagram_shadow.html', op = asdict(success_response))
		# return Response(msg, status=400, mimetype='application/json')
	else:	
		msg = ErrorResponse(status=0, message="Could download data from Geodesignhub, please check your project ID and API token.",code=400)
		return Response(msg, status=400, mimetype='application/json')


if __name__ == '__main__':
	app.debug = True
	port = int(os.environ.get("PORT", 5001))
	app.run(port =5001)
