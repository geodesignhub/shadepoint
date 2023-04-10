
import arrow
import pandas as pd
from data_definitions import ShadowGenerationRequest
from dacite import from_dict
import geopandas as gpd
import pybdshadow
from conn import get_redis
r = get_redis()



def compute_building_shadow(buildings_date_time: dict):
    _building_date_time = from_dict(data_class = ShadowGenerationRequest, data = buildings_date_time)
    _date_time = arrow.get(_building_date_time.date_time)
    
    buildings = gpd.GeoDataFrame.from_features(_building_date_time.geojson['features'])
    _pd_date_time =pd.to_datetime(_date_time.isoformat()).tz_convert('UTC')
    
    shadows = pybdshadow.bdshadow_sunlight(buildings,_pd_date_time)

    print(shadows.to_json())
