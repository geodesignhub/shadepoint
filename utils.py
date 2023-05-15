
import arrow
import time
import pandas as pd
from data_definitions import ShadowGenerationRequest, RoadsDownloadRequest, RoadsShadowOverlap
from dacite import from_dict

import geopandas as gpd
import pybdshadow
from shapely.geometry import Polygon, LineString
import json
from typing import List
import requests
import numpy as np
from conn import get_redis
from shapely.prepared import prep
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
            print(fc)
            r.set(roads_storage_key, json.dumps(fc))
        else: 
            print("Error")
            r.set(roads_storage_key, json.dumps({"type":"FeatureCollection", "features":[]}))
        
        r.expire(roads_storage_key, time = 60000)
        
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


def compute_shadow(geojson_session_date_time: dict):
    _diagramid_building_date_time = from_dict(data_class = ShadowGenerationRequest, data = geojson_session_date_time)
    
    _date_time = arrow.get(_diagramid_building_date_time.request_date_time).isoformat()
    
    buildings = gpd.GeoDataFrame.from_features(_diagramid_building_date_time.geojson['features'])
    _pd_date_time =pd.to_datetime(_date_time).tz_convert('UTC')    
    shadows = pybdshadow.bdshadow_sunlight(buildings,_pd_date_time)    
    redis_key = _diagramid_building_date_time.session_id +':' +  _diagramid_building_date_time.request_date_time
    r.set(redis_key, json.dumps(shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    print("Job Completed")
    
def compute_road_shadow_overlap(shadow_geojson, bounds) -> RoadsShadowOverlap: 

    r_url = os.environ.get("ROADS_URL", None)
    roads_url = r_url.replace('__bounds__', bounds)
    roads = download_roads(bounds=bounds, roads_url=roads_url)

    intersections: List[LineString] = []
    all_roads: List[LineString] = []
    all_shadows: List[Polygon] = []
    
    for line_feature in roads['features']:


        l = LineString(coordinates = line_feature['geometry']['cooridnates'])
        all_roads.append(l)

    for shadow_feature in shadow_geojson['features']:
        s = Polygon(shadow_feature['geometry']['coordinates'])
        all_shadows.append(s)

    roads_tree = STRtree(all_roads)

    for current_s in all_shadows:
        relevant_roads = [all_roads[idx] for idx in roads_tree.query(current_s, predicate="intersects")]
        print(relevant_roads)

        for relevant_road in relevant_roads:
            intersection = relevant_road.intersects(current_s)
            intersections.append(intersection)

    print(intersections)



    # hits = filter(prepared_polygon.intersects, all_roads)
    

