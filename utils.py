
import arrow
import pandas as pd
from data_definitions import ShadowGenerationRequest
from dacite import from_dict
import geopandas as gpd
import pybdshadow
import json
from conn import get_redis
r = get_redis()



def compute_building_shadow(diagramid_buildings_date_time: dict):
    _diagramid_building_date_time = from_dict(data_class = ShadowGenerationRequest, data = diagramid_buildings_date_time)
    _date_time = arrow.get(_diagramid_building_date_time.date_time).isoformat()
    
    buildings = gpd.GeoDataFrame.from_features(_diagramid_building_date_time.geojson['features'])
    _pd_date_time =pd.to_datetime(_date_time).tz_convert('UTC')
    
    shadows = pybdshadow.bdshadow_sunlight(buildings,_pd_date_time)

    redis_key = _diagramid_building_date_time.session_id

    r.set(redis_key, json.dumps(shadows.to_json()))
    r.expire(redis_key, time=6000)
    
