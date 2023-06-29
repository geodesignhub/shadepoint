#!/usr/bin/env python3

from flask import render_template
from flask import request, Response
from dataclasses import asdict
from data_definitions import ErrorResponse, DiagramShadowSuccessResponse, GeodesignhubDiagramGeoJSON, DesignShadowSuccessResponse,RoadsShadowOverlap
import arrow
import uuid
from download_helper import GeodesignhubDataDownloader, ShadowComputationHelper
import json
from conn import get_redis
import os
import geojson
from dotenv import load_dotenv, find_dotenv
from dashboard import create_app

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

@app.route('/generated_shadow', methods = ['GET'])
def get_diagram_shadow():
	shadow_key = request.args.get('shadow_key', '0')	
	
	shadow_exists = redis.exists(shadow_key)
	
	if shadow_exists: 
		s = redis.get(shadow_key)	
		shadow = json.loads(s)
	else: 
		shadow = {"type":"FeatureCollection", "features":[]}
	
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
		roads = {"type":"FeatureCollection", "features":[]}
		
	rds = json.dumps(roads)
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
		trees = {"type":"FeatureCollection", "features":[]}
		
	trs = json.dumps(trees)
	
	return Response(trs, status=200, mimetype='application/json')
	

@app.route('/get_shadow_roads_stats', methods = ['GET'])
def generate_shadow_road_stats():
	roads_shadow_stats_key = request.args.get('roads_shadow_stats_key', '0')
	
	print(roads_shadow_stats_key)
	roads_shadow_stats_exists = redis.exists(roads_shadow_stats_key)
	print(roads_shadow_stats_exists)
	if roads_shadow_stats_exists: 
		s = redis.get(roads_shadow_stats_key)	
		shadow_stats = json.loads(s)
	else: 
		default_shadow =  RoadsShadowOverlap(total_roads_kms=0.0, shadowed_kms=0.0, job_id = '0000')
		shadow_stats = asdict(default_shadow)
	print(shadow_stats)
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
		my_geodesignhub_downloader = GeodesignhubDataDownloader(session_id = session_id, project_id= projectid, synthesis_id=synthesisid, cteam_id= cteamid, apitoken=apitoken)

		project_data = my_geodesignhub_downloader.download_project_data_from_geodesignhub()
		if not project_data:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')

		_design_feature_collection = my_geodesignhub_downloader.download_design_data_from_geodesignhub()
		gj_serialized = json.loads(geojson.dumps(_design_feature_collection))

		design_geojson = GeodesignhubDiagramGeoJSON(geojson = gj_serialized)
		
		shadow_computation_helper = ShadowComputationHelper(session_id = str(session_id),  design_diagram_geojson = gj_serialized, shadow_date_time = shadow_date_time, bounds = project_data.bounds.bounds)
		shadow_computation_helper.compute_buildings_shadow()
		# worker_data = GeodesignhubDataShadowGenerationRequest(design_diagram_geojson = gj_serialized, session_id = str(session_id), request_date_time = shadow_date_time)

		# result = q.enqueue(utils.compute_shadow,asdict(worker_data), on_success= notify_shadow_complete, on_failure = shadow_generation_failure, job_id = str(session_id) + ":"+ shadow_date_time)


		# Download Data		
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
		## Download data from GDH
		my_geodesignhub_downloader = GeodesignhubDataDownloader(session_id = session_id, project_id= projectid, diagram_id=diagramid, apitoken=apitoken)
		project_data = my_geodesignhub_downloader.download_project_data_from_geodesignhub()
		if not project_data:
			error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
			return Response(asdict(error_msg), status=400, mimetype='application/json')
		else:
			_diagram_feature_collection = my_geodesignhub_downloader.download_diagram_data_from_geodesignhub()
			gj_serialized = json.loads(geojson.dumps(_diagram_feature_collection))
			diagram_geojson = GeodesignhubDiagramGeoJSON(geojson = gj_serialized)			
			maptiler_key = os.getenv('maptiler_key', '00000000000000')			
			shadow_computation_helper = ShadowComputationHelper(session_id = str(session_id),  design_diagram_geojson = gj_serialized, shadow_date_time = shadow_date_time, bounds = project_data.bounds.bounds)
			shadow_computation_helper.compute_buildings_shadow()
			success_response = DiagramShadowSuccessResponse(status=1,message="Data from Geodesignhub retrieved",diagram_geojson= diagram_geojson, project_data = project_data, maptiler_key=maptiler_key, session_id = str(session_id))		
							
			
			return render_template('diagram_shadow.html', op = asdict(success_response))		
	else:	
		msg = ErrorResponse(status=0, message="Could download data from Geodesignhub, please check your project ID and API token.",code=400)
		return Response(msg, status=400, mimetype='application/json')

if __name__ == '__main__':
	app.debug = True
	port = int(os.environ.get("PORT", 5001))
	app.run(port =port)