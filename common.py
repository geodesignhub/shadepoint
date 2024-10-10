from geojson import Polygon, Feature, FeatureCollection
from data_definitions import DrawnTreesFeatureProperties
import uuid

def parse_geojson_to_feature_collection(geojson) -> FeatureCollection:
    _feature_property = DrawnTreesFeatureProperties(
        height=10, base_height=0, color="#FF0000", building_id=str(uuid.uuid4())
    )
    _all_features = []
    _features = geojson['features']
    for _feature in _features:
        f = Feature(geometry=Polygon(_feature["geometry"]["coordinates"]), properties=_feature_property)        
        _all_features.append(f)
                
    feature_collection = FeatureCollection(_all_features)
    return feature_collection