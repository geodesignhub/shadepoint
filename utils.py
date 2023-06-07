
import arrow
import time
import pandas as pd
from data_definitions import GeodesignhubDataShadowGenerationRequest, RoadsDownloadRequest, RoadsShadowOverlap,ShadowsRoadsIntersectionRequest, TreesDownloadRequest, TreeData, RoadsShadowsComputationStartRequest
from dacite import from_dict
from pyproj import Geod
import geopandas as gpd
import pybdshadow
from shapely.geometry import Polygon, LineString
from shapely.geometry import shape
from shapely.geometry.polygon import Polygon
import json
import uuid
from typing import List
import requests
import numpy as np
from dataclasses import asdict
from conn import get_redis
from shapely import STRtree
import os
import hashlib
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

r = get_redis()


def download_roads(roads_download_request: RoadsDownloadRequest):
    _roads_download_request = from_dict(data_class = RoadsDownloadRequest, data = roads_download_request)
    bounds = _roads_download_request.bounds
    roads_url =_roads_download_request.roads_url
    session_roads_key = _roads_download_request.session_id +':' + _roads_download_request.request_date_time +':' +  'roads'
    bounds_hash= hashlib.sha512(bounds.encode('utf-8')).hexdigest()
    
    '''A function to download roads GeoJSON from GDH data server for the given bounds,  '''
    fc = {"type":"FeatureCollection","features":[]}
    roads_storage_key = bounds_hash[:15] + ':roads'
    r.set(session_roads_key, roads_storage_key)
    r.expire(session_roads_key, time =6000)
    
    if r.exists(roads_storage_key):
        fc_str = r.get(roads_storage_key)
        fc = json.loads(fc_str)

    else: 
        # r_url = roads_url.replace('__bounds__', bounds)
        r_url = roads_url
        download_request = requests.get(r_url)
        
        if download_request.status_code == 200:
            fc = download_request.json()    
            r.set(roads_storage_key, json.dumps(fc))
        else: 
            print("Error")
            r.set(roads_storage_key, json.dumps({"type":"FeatureCollection", "features":[]}))
        
        r.expire(roads_storage_key, time = 60000)
        
    return fc


def download_trees(trees_download_request: TreesDownloadRequest):
    _trees_download_request = from_dict(data_class = TreesDownloadRequest, data = trees_download_request)
    bounds = _trees_download_request.bounds
    trees_url =_trees_download_request.trees_url
    session_trees_key = _trees_download_request.session_id +':' + _trees_download_request.request_date_time +':' +  'trees'
    bounds_hash= hashlib.sha512(bounds.encode('utf-8')).hexdigest()
    
    
    '''A function to download roads GeoJSON from GDH data server for the given bounds,  '''
    fc = {"type":"FeatureCollection","features":[]}
    trees_storage_key = bounds_hash[:15] + ':trees'
    
    r.set(session_trees_key, trees_storage_key)
    r.expire(session_trees_key, time =6000)
    
    if r.exists(trees_storage_key):
        fc_str = r.get(trees_storage_key)
        fc = json.loads(fc_str)

    else:         
        t_url = trees_url
        download_request = requests.get(t_url)
        
        if download_request.status_code == 200:
            fc = download_request.json()    
            r.set(trees_storage_key, json.dumps(fc))
        else: 
            print("Error")
            r.set(trees_storage_key, json.dumps({"type":"FeatureCollection", "features":[]}))
        
        r.expire(trees_storage_key, time = 60000)
        
    return fc


def create_point_grid(geojson_feature):
    """ This function takes a policy polygon feature and generates a point grid """
    
    x_spacing = .001 #The point spacing you want
    y_spacing = .001
    df = gpd.GeoDataFrame.from_features([geojson_feature])

    xmin, ymin, xmax, ymax = df.total_bounds #Find the bounds of all polygons in the df
    xcoords = [c for c in np.arange(xmin, xmax, x_spacing)] #Create x coordinates
    ycoords = [c for c in np.arange(ymin, ymax, y_spacing)] #And y

    coordinate_pairs = np.array(np.meshgrid(xcoords, ycoords)).T.reshape(-1, 2) #Create all combinations of xy coordinates
    geometries = gpd.points_from_xy(coordinate_pairs[:,0], coordinate_pairs[:,1]) #Create a list of shapely points

    point_df = gpd.GeoDataFrame(geometry=geometries, crs=df.crs) #Create the point df
    point_df['geometry'] = point_df['geometry'].buffer(0.00005)
    point_json = point_df.to_json()
    point_gj = json.loads(point_json)
    # TODO Filter the points to keep within bounds of the polygon
    #filtered_points = df.within(df.at[0,'geometry'])
    #print(filtered_points)
    return point_gj

def kickoff_roads_shadows_stats(roads_shadow_computation_start):
    _roads_shadow_computation_details = from_dict(data_class = RoadsShadowsComputationStartRequest, data = roads_shadow_computation_start)
    
    
    shadows_key = _roads_shadow_computation_details.session_id +':' +  _roads_shadow_computation_details.request_date_time
    shadows_str = r.get(shadows_key)
    shadows = json.loads(shadows_str.decode('utf-8'))

    bounds = _roads_shadow_computation_details.bounds

    bounds_hash= hashlib.sha512(bounds.encode('utf-8')).hexdigest()
    roads_storage_key = bounds_hash[:15] + ':roads'
    roads_str = r.get(roads_storage_key)
    roads = json.loads(roads_str.decode('utf-8'))
    
    shadow_roads_intersection_data = ShadowsRoadsIntersectionRequest(roads= json.dumps(roads), shadows=shadows, job_id =_roads_shadow_computation_details.session_id + ':roads_shadow"' )
    compute_road_shadow_overlap(roads_shadows_data = asdict(shadow_roads_intersection_data))
    # print(shadow_roads_intersection_data)	

def compute_shadow(geojson_session_date_time: dict):
    _diagramid_building_date_time = from_dict(data_class = GeodesignhubDataShadowGenerationRequest, data = geojson_session_date_time)
    
    _date_time = arrow.get(_diagramid_building_date_time.request_date_time).isoformat()
    
    buildings = gpd.GeoDataFrame.from_features(_diagramid_building_date_time.buildings['features'])
    _pd_date_time =pd.to_datetime(_date_time).tz_convert('UTC')    
    shadows = pybdshadow.bdshadow_sunlight(buildings,_pd_date_time) 
    dissolved_shadows = shadows.dissolve()   
    redis_key = _diagramid_building_date_time.session_id +':' +  _diagramid_building_date_time.request_date_time
    r.set(redis_key, json.dumps(dissolved_shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    print("Job Completed")


def compute_shadow_with_trees(geojson_session_date_time: dict):
    _diagramid_building_date_time = from_dict(data_class = GeodesignhubDataShadowGenerationRequest, data = geojson_session_date_time)
    
    _date_time = arrow.get(_diagramid_building_date_time.request_date_time).isoformat()
    bounds = _diagramid_building_date_time.bounds
    # Combine trees and buildings into one FC
    bounds_hash= hashlib.sha512(bounds.encode('utf-8')).hexdigest()
    tress_buildings_features = _diagramid_building_date_time.buildings['features']
    bounds_hash_key = bounds_hash[:15] + ':trees'
    downloaded_trees_raw = r.get(bounds_hash_key)

    downloaded_trees_fc = json.loads(downloaded_trees_raw)    
    downloaded_trees_features = downloaded_trees_fc['features']
    for tree_feature in downloaded_trees_features:
        tree_properties = {}        
        _tree_height = TreeData(height=10, base_height=0)
        tree_properties['height'] = asdict(_tree_height)['height']
        tree_properties['base_height'] = asdict(_tree_height)['base_height']
        tree_properties['tree_id'] = str(uuid.uuid4())    
        tree_feature['properties'] = tree_properties
        tress_buildings_features.append(tree_feature)


    buildings = gpd.GeoDataFrame.from_features(tress_buildings_features)
    _pd_date_time =pd.to_datetime(_date_time).tz_convert('UTC')    
    shadows = pybdshadow.bdshadow_sunlight(buildings,_pd_date_time) 
    dissolved_shadows = shadows.dissolve()   
    redis_key = _diagramid_building_date_time.session_id +':' +  _diagramid_building_date_time.request_date_time
    r.set(redis_key, json.dumps(dissolved_shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    print("Job Completed")
    
def compute_road_shadow_overlap(roads_shadows_data:ShadowsRoadsIntersectionRequest) -> RoadsShadowOverlap: 
    
    _roads_shadows_data = from_dict(data_class = ShadowsRoadsIntersectionRequest, data = roads_shadows_data)
    roads_str = _roads_shadows_data.roads
    shadows_str = _roads_shadows_data.shadows

    job_id = _roads_shadows_data.job_id
    geod = Geod(ellps="WGS84")
    roads = json.loads(roads_str)    
    shadows = json.loads(shadows_str)
    
    
    intersections: List[LineString] = []
    all_roads: List[LineString] = []
    all_shadows: List[Polygon] = []

    total_length = 0
    shadowed_kms = 0
    
    for line_feature in roads['features']:
        l = LineString(coordinates = line_feature['geometry']['coordinates'])
        all_roads.append(l)        
        segment_length = geod.geometry_length(l)

        print("Segment Length {segment_length:.3f}".format(segment_length= segment_length))
        total_length += segment_length

    for shadow_feature in shadows['features']:       
        
        s: Polygon = shape(shadow_feature['geometry'])
        all_shadows.append(s)

    roads_tree = STRtree(all_roads)

    for current_s in all_shadows:
        relevant_roads = [all_roads[idx] for idx in roads_tree.query(current_s, predicate="intersects")]

        for relevant_road in relevant_roads:
            # line_buffered = relevant_road.buffer(0.0001)
            intersection = relevant_road.intersection(current_s)
            intersection_length = geod.geometry_length(intersection)
            
            print("Intersection Length {intersection_length:.3f}".format(intersection_length= intersection_length))

            intersections.append(intersection)
            shadowed_kms += intersection_length

    road_shadow_overlap = RoadsShadowOverlap(total_roads_kms=round(total_length,2), shadowed_kms=round(shadowed_kms,2), job_id = job_id)

    r.set(job_id, json.dumps(asdict(road_shadow_overlap)))
    time.sleep(1)
    print("Intersection Completed")
    
