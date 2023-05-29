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
from data_definitions import ErrorResponse, DiagramShadowSuccessResponse, GeodesignhubProjectBounds, GeodesignhubSystem, GeodesignhubProjectData, GeodesignhubDiagramGeoJSON, GeodesignhubFeatureProperties,BuildingData, ShadowGenerationRequest, GeodesignhubDesignFeatureProperties, DesignShadowSuccessResponse, RoadsDownloadRequest, ShadowsRoadsIntersectionRequest, RoadsShadowOverlap,TreesDownloadRequest, GeodesignhubProjectCenter
import arrow
import uuid
import utils
from conn import get_redis
import os
import geojson
from dotenv import load_dotenv, find_dotenv
from dashboard import create_app
from notifications_helper import notify_shadow_complete, shadow_generation_failure, notify_roads_download_complete, notify_roads_download_failure, notify_roads_shadow_intersection_complete, notify_roads_shadow_intersection_failure, notify_trees_download_complete, notify_trees_download_failure

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
	

@app.route('/get_downloaded_roads', methods = ['GET'])
def get_downloaded_roads():
	roads_key = request.args.get('roads_key', '0')	
	roads_session_exists = redis.exists(roads_key)
	if roads_session_exists: 
		roads_data_key = redis.get(roads_key)	
		r_raw = redis.get(roads_data_key)			
		roads = json.loads(r_raw.decode('utf-8'))
	else: 
		roads = {}
		
	# TODO: Kick off compute_road_shadow_overlap and use the same roads_key
	
	rds = json.dumps(roads)
	shadows_key = roads_key[:-6]
	shadows_str = redis.get(shadows_key)
	
	job_id = roads_key.split(':')[0] + ':roads_shadow"'
	shadows = json.loads(shadows_str.decode('utf-8'))

	shadow_roads_intersection_job = ShadowsRoadsIntersectionRequest(roads= rds, job_id = job_id, shadows= shadows)

	# print(shadow_roads_intersection_job)		
	roads_intersection_result = q.enqueue(utils.compute_road_shadow_overlap, asdict(shadow_roads_intersection_job), on_success= notify_roads_shadow_intersection_complete, on_failure = notify_roads_shadow_intersection_failure, job_id = job_id )

	return Response(rds, status=200, mimetype='application/json')
	
@app.route('/get_downloaded_trees', methods = ['GET'])
def get_downloaded_trees():
	trees_key = request.args.get('trees_key', '0')	
	trees_session_exists = redis.exists(trees_key)
	if trees_session_exists: 
		trees_data_key = redis.get(trees_key)	
		r_raw = redis.get(trees_data_key)			
		trees = json.loads(r_raw.decode('utf-8'))
	else: 
		trees = {}
		
	# TODO: Kick off compute_road_shadow_overlap and use the same roads_key
	
	trs = json.dumps(trees)
	print('here')
	# shadows_key = trees_key[:-6]
	# shadows_str = redis.get(shadows_key)
	
	# job_id = trees_key.split(':')[0] + ':trees_shadow"'
	# shadows = json.loads(shadows_str.decode('utf-8'))

	# shadow_roads_intersection_job = ShadowsRoadsIntersectionRequest(roads= rds, job_id = job_id, shadows= shadows)

	# # print(shadow_roads_intersection_job)		
	# roads_intersection_result = q.enqueue(utils.compute_road_shadow_overlap, asdict(shadow_roads_intersection_job), on_success= notify_roads_shadow_intersection_complete, on_failure = notify_roads_shadow_intersection_failure, job_id = job_id )

	return Response(trs, status=200, mimetype='application/json')
	

@app.route('/get_shadow_roads_stats', methods = ['GET'])
def generate_shadow_road_stats():
	roads_shadow_stats_key = request.args.get('roads_shadow_stats_key', '0')	
	roads_shadow_stats_exists = redis.exists(roads_shadow_stats_key)
	if roads_shadow_stats_exists: 
		s = redis.get(roads_shadow_stats_key)	
		shadow_stats = json.loads(s)
	else: 
		default_shadow =  RoadsShadowOverlap(total_roads_kms=0.0, shadowed_kms=0.0, job_id = '0000')
		shadow_stats = asdict(default_shadow)

	return Response(json.dumps(shadow_stats), status=200, mimetype='application/json')
	

@app.route('/design_shadow/', methods = ['GET'])
def generate_design_shadow():	
	try:
		projectid = request.args.get('projectid')
		apitoken = request.args.get('apitoken')
		synthesisid = request.args.get('synthesisid')
		cteamid = request.args.get('cteamid')

	except KeyError as e:
		error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Design Team ID / Design ID or API Token ID. One or more of these were not found in your request.",code=400)
		return Response(asdict(error_msg), status=400, mimetype='application/json')
	try:
		r_date_time = request.args.get('date_time', None)
		if not r_date_time:
			raise KeyError
		else:
			shadow_date_time = arrow.get(r_date_time).format('YYYY-MM-DDTHH:mm:ss')		
	except KeyError as ke: 
		shadow_date_time = arrow.now().format('YYYY-MM-DDTHH:mm:ss')

	if projectid and cteamid and apitoken and synthesisid:
		
		session_id = uuid.uuid4()
		
		# Initialize the API
		myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=projectid, token=apitoken)
		# Download Data		
		s = myAPIHelper.get_all_systems()
		b = myAPIHelper.get_project_bounds()
		c = myAPIHelper.get_project_center()
		r = myAPIHelper.get_single_synthesis(teamid = int(cteamid), synthesisid = synthesisid)
		
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
			assert r.status_code == 200
		except AssertionError as ae:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')

		_design_details_raw = r.json()
		_all_features: List[Feature] = []
		# Populate Default building data if not available
		for _single_diagram_feature in _design_details_raw['features']:
			_diagram_properties = _single_diagram_feature['properties']
			_project_or_policy = _diagram_properties['areatype']
			_diagram_properties['height'] = _diagram_properties['max_height']
			_diagram_properties['base_height'] = _diagram_properties['min_height']
			_diagram_properties['diagram_id'] = _diagram_properties['diagramid']
			_diagram_properties['building_id'] = str(uuid.uuid4())
			
			_feature_properties = from_dict(data_class = GeodesignhubDesignFeatureProperties, data = _diagram_properties)
				
			if _project_or_policy =='policy':
				point_grid = utils.create_point_grid(geojson_feature=_single_diagram_feature)
				
				_feature_properties.height = 0
				_feature_properties.base_height = 0
				for _point_feature in point_grid['features']:
					_point_geometry = Polygon(coordinates=_point_feature['geometry']['coordinates'])
					_feature = Feature(geometry=_point_geometry, properties=asdict(_feature_properties))
					_all_features.append(_feature)
			else:				
				# We assume that GDH will provide a polygon
				if _single_diagram_feature['geometry']['type'] == 'Polygon':					
					_geometry = Polygon(coordinates=_single_diagram_feature['geometry']['coordinates'])
				elif _single_diagram_feature['geometry']['type'] == 'LineString':
					_geometry = LineString(coordinates=_single_diagram_feature['geometry']['coordinates'])
				else: 
					error_msg = ErrorResponse(status=0, message="Building shadows can only be computed for polygon features, you are trying to compute shadows for .",code=400)
					return Response(asdict(error_msg), status=400, mimetype='application/json')
				_feature = Feature(geometry=_geometry, properties=asdict(_feature_properties))
				_all_features.append(_feature)

		_diagram_feature_collection = FeatureCollection(features=_all_features)
		gj_serialized = json.loads(geojson.dumps(_diagram_feature_collection))

		design_geojson = GeodesignhubDiagramGeoJSON(geojson = gj_serialized)

		worker_data = ShadowGenerationRequest(geojson = design_geojson.geojson, session_id = str(session_id), request_date_time = shadow_date_time)

		result = q.enqueue(utils.compute_shadow,asdict(worker_data), on_success= notify_shadow_complete, on_failure = shadow_generation_failure, job_id = str(session_id) + ":"+ shadow_date_time)

		try:
			assert b.status_code == 200
		except AssertionError as ae:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')

		center = from_dict(data_class=GeodesignhubProjectCenter,data = c.json())
		bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())			
		project_data = GeodesignhubProjectData(systems=all_systems , bounds=bounds, center=center)
		
		maptiler_key = os.getenv('maptiler_key', '00000000000000')
		success_response = DesignShadowSuccessResponse(status=1,message="Data from Geodesignhub retrieved",design_geojson= design_geojson, project_data = project_data, maptiler_key=maptiler_key, session_id = str(session_id))
		
		
		return render_template('design_shadow.html', op = asdict(success_response))
		# return Response(msg, status=400, mimetype='application/json')
	else:	
		msg = ErrorResponse(status=0, message="Could download data from Geodesignhub, please check your project ID and API token.",code=400)
		return Response(msg, status=400, mimetype='application/json')

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
		c = myAPIHelper.get_project_center()
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
		result = q.enqueue(utils.compute_shadow,asdict(worker_data), on_success= notify_shadow_complete, on_failure = shadow_generation_failure, job_id = str(session_id) + ":"+ shadow_date_time)

		try:
			assert b.status_code == 200
		except AssertionError as ae:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')
		center = from_dict(data_class=GeodesignhubProjectCenter,data = c.json())
		bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())			
		project_data = GeodesignhubProjectData(systems=all_systems ,bounds=bounds, center=center)		
		
		r_url = os.getenv("ROADS_URL", None)
		# download the roads 
		if r_url:			
			roads_download_job = RoadsDownloadRequest(bounds= bounds.bounds,  session_id = str(session_id), request_date_time=shadow_date_time,roads_url=r_url)
			roads_download_result = q.enqueue(utils.download_roads, asdict(roads_download_job), on_success= notify_roads_download_complete, on_failure = notify_roads_download_failure, job_id = str(session_id) + ":"+ shadow_date_time +":roads")
		t_url = os.getenv("TREES_URL", None)
		# download the roads 
		if t_url:			
			trees_download_job = TreesDownloadRequest(bounds= bounds.bounds,  session_id = str(session_id), request_date_time=shadow_date_time,trees_url=t_url)
			trees_download_result = q.enqueue(utils.download_trees, asdict(trees_download_job), on_success= notify_trees_download_complete, on_failure = notify_trees_download_failure, job_id = str(session_id) + ":"+ shadow_date_time +":trees")

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