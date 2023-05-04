
import arrow
import time
import pandas as pd
from data_definitions import ShadowGenerationRequest
from dacite import from_dict

import geopandas as gpd
import pybdshadow
import json
import numpy as np
from conn import get_redis
r = get_redis()


def create_point_grid(geojson_feature):
    
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
    
