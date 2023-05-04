#!/usr/bin/env python3
from flask import Flask
from flask import render_template
from flask import request, Response
import json, GeodesignHub
import config
from dataclasses import asdict
from dacite import from_dict
from typing import List
from geojson import Feature, FeatureCollection, Polygon, LineString
from data_definitions import ErrorResponse, DiagramShadowSuccessResponse, GeodesignhubProjectBounds, GeodesignhubSystem, GeodesignhubProjectData, GeodesignhubDiagramGeoJSON, GeodesignhubFeatureProperties,BuildingData, ShadowGenerationRequest
import arrow
import uuid
import utils
from conn import get_redis
import os
import geojson
from dotenv import load_dotenv, find_dotenv
from dashboard import create_app
from notifications_helper import notify_shadow_complete, shadow_generation_failure

from rq import Queue
from worker import conn

load_dotenv(find_dotenv())

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

redis = get_redis()
q = Queue(connection=conn)

app = create_app()

@app.route('/', methods = ['GET'])
def home():
	return render_template('home.html')


@app.route('/generated_diagram_shadow', methods = ['GET'])
def get_diagram_shadow():
	shadow_key = request.args.get('shadow_key', '0')	
	shadow_exists = redis.exists(shadow_key)
	if shadow_exists: 
		s = redis.get(shadow_key)	
		shadow = json.loads(s)
	else: 
		shadow = {}

	return Response(shadow, status=200, mimetype='application/json')
	
@app.route('/diagram_shadow/', methods = ['GET'])
def generate_diagram_shadow():
	''' This is the root of the webservice, upon successful authentication a text will be displayed in the browser '''
	try:
		projectid = request.args.get('projectid')
		apitoken = request.args.get('apitoken')
		diagramid = request.args.get('diagramid')

	except KeyError as e:
		error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
		return Response(asdict(error_msg), status=400, mimetype='application/json')
	try:
		r_date_time = request.args.get('date_time', None)
		if not r_date_time:
			raise KeyError
		else:
			shadow_date_time = arrow.get(r_date_time).format('YYYY-MM-DDTHH:mm:ss')		
	except KeyError as ke: 
		shadow_date_time = arrow.now().format('YYYY-MM-DDTHH:mm:ss')

	if projectid and diagramid and apitoken:
		
		session_id = uuid.uuid4()
		
		# Initialize the API
		myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=projectid, token=apitoken)
		# Download Data		
		s = myAPIHelper.get_all_systems()
		b = myAPIHelper.get_project_bounds()
		diagram_id = int(diagramid)
		d = myAPIHelper.get_single_diagram(diagid = diagram_id)
		
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
		# Populate Default building data if not available
		if not bool(_diagram_details_raw['building_data']):
			_default_building_data = {"storeys_above_ground": 10,"storeys_below_ground": 0}
		else: 
			_default_building_data = _diagram_details_raw['building_data']

		_diagram_details_feature_collection = _diagram_details_raw['geojson']
		
		_all_features: List[Feature] = []
		for f in _diagram_details_feature_collection['features']:			
			_f_props = f['properties']
			_building_data = BuildingData(height=_default_building_data['storeys_above_ground']* 4.5, base_height=_default_building_data['storeys_below_ground']* 4.5)

			_diagram_details_raw['height'] = asdict(_building_data)['height']
			_diagram_details_raw['base_height'] = asdict(_building_data)['base_height']
			_diagram_details_raw['diagram_id'] = diagram_id
			_diagram_details_raw['building_id'] = str(uuid.uuid4())
			
			_diagram_details_raw['color'] = _f_props['color']
			_feature_properties = from_dict(data_class = GeodesignhubFeatureProperties, data = _diagram_details_raw)
			
			# We assume that GDH will provide a polygon
			if f['geometry']['type'] == 'Polygon':					
				_geometry = Polygon(coordinates=f['geometry']['coordinates'])
			elif f['geometry']['type'] == 'LineString':
				_geometry = LineString(coordinates=f['geometry']['coordinates'])
			else: 
				error_msg = ErrorResponse(status=0, message="Building shadows can only be computed for polygon features, you are trying to compute shadows for .",code=400)
				return Response(asdict(error_msg), status=400, mimetype='application/json')
			_feature = Feature(geometry=_geometry, properties=asdict(_feature_properties))
			_all_features.append(_feature)

		_diagram_feature_collection = FeatureCollection(features=_all_features)
		gj_serialized = json.loads(geojson.dumps(_diagram_feature_collection))

		diagram_geojson = GeodesignhubDiagramGeoJSON(geojson = gj_serialized)

		worker_data = ShadowGenerationRequest(geojson = diagram_geojson.geojson, session_id = str(session_id), request_date_time = shadow_date_time)
		result = q.enqueue(utils.compute_building_shadow,asdict(worker_data), on_success= notify_shadow_complete, on_failure = shadow_generation_failure, job_id = str(session_id) + ":"+shadow_date_time)

		try:
			assert b.status_code == 200
		except AssertionError as ae:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')

		bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())			
		project_data = GeodesignhubProjectData(systems=all_systems ,bounds=bounds)		
		
		maptiler_key = os.getenv('maptiler_key', '00000000000000')
		success_response = DiagramShadowSuccessResponse(status=1,message="Data from Geodesignhub retrieved",diagram_geojson= diagram_geojson, project_data = project_data, maptiler_key=maptiler_key, session_id = str(session_id))
		
		
		return render_template('diagram_shadow.html', op = asdict(success_response))
		# return Response(msg, status=400, mimetype='application/json')
	else:	
		msg = ErrorResponse(status=0, message="Could download data from Geodesignhub, please check your project ID and API token.",code=400)
		return Response(msg, status=400, mimetype='application/json')

if __name__ == '__main__':
	app.debug = True
	port = int(os.environ.get("PORT", 5001))
	app.run(port =port)