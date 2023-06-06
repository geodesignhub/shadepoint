
from data_definitions import ErrorResponse, DiagramShadowSuccessResponse, GeodesignhubProjectBounds, GeodesignhubSystem, GeodesignhubProjectData, GeodesignhubDiagramGeoJSON, GeodesignhubFeatureProperties,BuildingData, GeodesignhubDataShadowGenerationRequest, GeodesignhubDesignFeatureProperties, DesignShadowSuccessResponse, RoadsDownloadRequest, ShadowsRoadsIntersectionRequest, RoadsShadowOverlap,TreesDownloadRequest, GeodesignhubProjectCenter
import utils
import os
from dataclasses import asdict
from dacite import from_dict
from typing import List, Optional
from geojson import Feature, FeatureCollection, Polygon, LineString
import GeodesignHub, config
from conn import get_redis
from dotenv import load_dotenv, find_dotenv
from dataclasses import asdict
from notifications_helper import notify_shadow_complete, shadow_generation_failure, notify_roads_download_complete, notify_roads_download_failure, notify_roads_shadow_intersection_complete, notify_roads_shadow_intersection_failure, notify_trees_download_complete, notify_trees_download_failure
from uuid import uuid4
import uuid
from rq import Queue
from worker import conn

load_dotenv(find_dotenv())

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

redis = get_redis()
q = Queue(connection=conn)

  

class GeodesignhubDataDownloader():
    """
    A class to download data from Geodesignhub
    """
    def __init__(self,session_id:uuid4,project_id:str, apitoken:str, cteam_id=None, synthesis_id = None, diagram_id = None ):
        self.session_id = session_id
        self.project_id = project_id
        self.apitoken = apitoken
        self.cteam_id = cteam_id
        self.synthesis_id = synthesis_id
        self.diagram_id = diagram_id
       

    def download_diagram_data_from_geodesignhub(self) -> Optional[FeatureCollection]:
        
        myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=self.projectid, token=self.apitoken)
        # Download Data		
        diagram_id = int(self.diagramid)
        d = myAPIHelper.get_single_diagram(diagid = diagram_id)

        try:
            assert d.status_code == 200
        except AssertionError as ae:
            error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)
            return None


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
                return None
            _feature = Feature(geometry=_geometry, properties=asdict(_feature_properties))
            _all_features.append(_feature)

        _diagram_feature_collection = FeatureCollection(features=_all_features)
        
        return _diagram_feature_collection
        

    def download_project_data_from_geodesignhub(self) -> Optional[GeodesignhubProjectData]:
        
        myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=self.projectid, token=self.apitoken)
        # Download Data		
        s = myAPIHelper.get_all_systems()
        b = myAPIHelper.get_project_bounds()
        c = myAPIHelper.get_project_center()
        diagram_id = int(self.diagramid)
        d = myAPIHelper.get_single_diagram(diagid = diagram_id)
        
        # Check responses / data
        try:
            assert s.status_code == 200
        except AssertionError as ae:			
            error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)                        
            return None
        
        systems = s.json()
        all_systems: List[GeodesignhubSystem] = []
        for s in systems:
            current_system = from_dict(data_class = GeodesignhubSystem, data = s)
            all_systems.append(current_system)
            
        try:
            assert d.status_code == 200
        except AssertionError as ae:
            error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)                        
            return None

        try:
            assert b.status_code == 200
        except AssertionError as ae:
            error_msg = ErrorResponse(status=0, message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",code=400)            
            return None

        center = from_dict(data_class=GeodesignhubProjectCenter,data = c.json())
        bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())			
        project_data = GeodesignhubProjectData(systems=all_systems ,bounds=bounds, center=center)	

        return project_data
    
        
class ShadowComputationHelper():

    def __init__(self, session_id:uuid4, shadow_date_time:str, bounds: str, geodesignhub_data, roads_data=None, trees_data=None, buildings_data=None ):
        self.geodesignhub_data = geodesignhub_data
        self.session_id = session_id
        self.shadow_date_time = shadow_date_time
        self.bounds = bounds        
        self.roads_data = roads_data
        self.trees_data = trees_data
        self.buildings_data = buildings_data
        self.combined_gdh_trees = {'type': 'FeatureCollection', 'features':[]}

    def download_roads_async(self,):
        roads_download_job = RoadsDownloadRequest(bounds= self.bounds,  session_id = str(self.session_id), request_date_time=self.shadow_date_time,roads_url=self.roads_url)
        roads_download_result = q.enqueue(utils.download_roads, asdict(roads_download_job), on_success= notify_roads_download_complete, on_failure = notify_roads_download_failure, job_id = str(self.session_id) + ":"+ self.shadow_date_time +":roads")

    def download_trees_async(self,):        
        trees_download_job = TreesDownloadRequest(bounds= self.bounds,  session_id = str(self.session_id), request_date_time=self.shadow_date_time,trees_url=self.trees_url)
        trees_download_result = q.enqueue(utils.download_trees, asdict(trees_download_job), on_success= notify_trees_download_complete, on_failure = notify_trees_download_failure, job_id = str(self.session_id) + ":"+ self.shadow_date_time +":trees")

    def combine_gdh_trees_data(self):
        ''' This method combines Geodesignhub and trees data and updates the combined_gdh_trees FeatureCollection '''

        raise NotImplementedError
    
    def compute_gdh_trees_shadow(self):
        ''' This method computes the GDH + trees shadow '''
        
        r_url = os.getenv("ROADS_URL", None)
        t_url = os.getenv("TREES_URL", None)
        b_url = os.getenv("BUILDINGS_URL", None)
        # download the roads 			
        if r_url:			
            self.download_roads_async()
        # download the roads 
        if t_url:			
            self.download_trees_async()
        # if b_url:			
        # 	my_downloads_helper.download_buildings_async()

        roads_download_job = RoadsDownloadRequest(bounds= self.bounds,  session_id = str(self.session_id), request_date_time=self.shadow_date_time,roads_url=self.roads_url)
        roads_download_result = q.enqueue(utils.download_roads, asdict(roads_download_job), on_success= notify_roads_download_complete, on_failure = notify_roads_download_failure, job_id = str(self.session_id) + ":"+ self.shadow_date_time +":roads")

        trees_download_job = TreesDownloadRequest(bounds= self.bounds,  session_id = str(self.session_id), request_date_time=self.shadow_date_time,trees_url=self.trees_url)
        trees_download_result = q.enqueue(utils.download_trees, asdict(trees_download_job), on_success= notify_trees_download_complete, on_failure = notify_trees_download_failure, job_id = str(self.session_id) + ":"+ self.shadow_date_time +":trees")

		# worker_data = GeodesignhubDataShadowGenerationRequest(geojson = self.combined_gdh_trees.geojson, session_id = str(session_id), request_date_time = shadow_date_time)
		# result = q.enqueue(utils.compute_shadow,asdict(worker_data), on_success= notify_shadow_complete, on_failure = shadow_generation_failure, job_id = str(session_id) + ":"+ shadow_date_time,  depends_on=[trees_download_job])
    