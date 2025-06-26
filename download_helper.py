from data_definitions import (
    ErrorResponse,
    GeodesignhubProjectBounds,
    GeodesignhubSystem,
    GeodesignhubProjectData,
    GeodesignhubFeatureProperties,
    BuildingData,
    GeodesignhubDataShadowGenerationRequest,
    GeodesignhubDesignFeatureProperties,
    RoadsDownloadRequest,
    TreesDownloadRequest,
    DrawnTreesFeatureProperties,
    GeodesignhubProjectCenter,
    RoadsShadowsComputationStartRequest,
    BuildingsDownloadRequest,
    ExistingBuildingsDataShadowGenerationRequest,
    GeodesignhubProjectTags,
    GeodesignhubSystemDetail,
    TreeFeatureProperties,
    DiagramUploadDetails,
    UploadSuccessResponse,
    DrawnTreesShadowGenerationRequest,
)
from dashboard.configurations.data_helper import ViewDataGenerator
import utils
from utils import GeometryHelper
from shapely.geometry.base import BaseGeometry
from shapely.geometry import mapping, shape
import json
from dataclasses import asdict
from dacite import from_dict
from typing import List, Optional, Union
from geojson import Feature, FeatureCollection, Polygon, LineString, Point
import GeodesignHub, config
from dashboard.conn import get_redis
from dotenv import load_dotenv, find_dotenv
from dataclasses import asdict
from notifications_helper import (
    notify_shadow_complete,
    shadow_generation_failure,
    notify_roads_download_complete,
    notify_roads_download_failure,
    notify_gdh_roads_shadow_intersection_complete,
    notify_gdh_roads_shadow_intersection_failure,
    notify_drawn_trees_shadow_complete,
    notify_drawn_trees_shadow_failure,
    notify_trees_download_complete,
    notify_trees_download_failure,
    notify_buildings_download_complete,
    notify_buildings_download_failure,
)

import hashlib
from uuid import uuid4
import uuid
from json import encoder
from rq import Queue
from rq.job import Dependency
from worker import conn
import arrow
import logging

logger = logging.getLogger("local-climate-response")

load_dotenv(find_dotenv())

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

redis = get_redis()
q = Queue(connection=conn)


class ShapelyEncoder(json.JSONEncoder):
    """Encodes JSON strings into shapes processed by SHapely"""

    def default(self, obj):
        if isinstance(obj, BaseGeometry):
            return mapping(obj)
        return json.JSONEncoder.default(self, obj)


def export_to_json(data):
    """Export a shapely output to JSON"""
    encoder.FLOAT_REPR = lambda o: format(o, ".6f")
    return json.loads(json.dumps(data, sort_keys=True, cls=ShapelyEncoder))


def kickoff_drawn_trees_shadow_job(
    session_id: str, state_id: str, unprocessed_drawn_trees: dict
):
    request_date_time = arrow.now().format("YYYY-MM-DDTHH:mm:ss")
    tree_processing_payload = DrawnTreesShadowGenerationRequest(
        trees=unprocessed_drawn_trees,
        session_id=session_id,
        state_id=state_id,
        request_date_time=request_date_time,
        processed_trees={},
    )
    job_id = session_id + "@drawn_trees_shadow_job"

    tree_processing_job_result = q.enqueue(
        utils.drawn_trees_compute_shadow,
        asdict(tree_processing_payload),
        on_success=notify_drawn_trees_shadow_complete,
        on_failure=notify_drawn_trees_shadow_failure,
        job_id=job_id,
    )


class GeodesignhubDataDownloader:
    """
    A class to download data from Geodesignhub
    """

    def __init__(
        self,
        session_id: str,
        project_id: str,
        apitoken: str,
        cteam_id=None,
        synthesis_id=None,
        diagram_id=None,
    ):
        self.session_id = session_id
        self.project_id = project_id
        self.apitoken = apitoken
        self.cteam_id = cteam_id
        self.synthesis_id = synthesis_id
        d = int(diagram_id) if diagram_id else None
        self.diagram_id = d
        self.api_helper = GeodesignHub.GeodesignHubClient(
            url=config.apisettings["serviceurl"],
            project_id=self.project_id,
            token=self.apitoken,
        )

    def download_project_systems(
        self,
    ) -> Union[ErrorResponse, List[GeodesignhubSystem]]:
        s = self.api_helper.get_all_systems()
        # Check responses / data
        try:
            assert s.status_code == 200
        except AssertionError as ae:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )

            return error_msg

        systems = s.json()
        all_systems: List[GeodesignhubSystem] = []
        for s in systems:
            current_system = from_dict(data_class=GeodesignhubSystem, data=s)
            all_systems.append(current_system)

        return all_systems

    def download_project_bounds(
        self,
    ) -> Union[ErrorResponse, GeodesignhubProjectBounds]:
        b = self.api_helper.get_project_bounds()
        try:
            assert b.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return error_msg

        bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())

        return bounds

    def download_project_tags(self) -> Union[ErrorResponse, GeodesignhubProjectTags]:
        t = self.api_helper.get_project_tags()
        try:
            assert t.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return error_msg
        return t.json()

    def upload_diagram(
        self, diagram_upload_details: DiagramUploadDetails
    ) -> Union[ErrorResponse, UploadSuccessResponse]:
        upload_job = self.api_helper.post_as_diagram(
            geoms=json.loads(diagram_upload_details.geometry),
            projectorpolicy=diagram_upload_details.project_or_policy,
            featuretype=diagram_upload_details.feature_type,
            description=diagram_upload_details.description,
            sysid=diagram_upload_details.sys_id,
            fundingtype=diagram_upload_details.funding_type,
        )

        job_result = upload_job.json()

        if upload_job.status_code == 201:
            upload_result = UploadSuccessResponse(
                message="Successfully uploaded diagram", code=201, status=1
            )

        else:
            upload_result = ErrorResponse(
                message=job_result["status"], code=400, status=0
            )

        return upload_result

    def download_project_center(
        self,
    ) -> Union[ErrorResponse, GeodesignhubProjectCenter]:
        c = self.api_helper.get_project_center()
        try:
            assert c.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )

            return error_msg
        center = from_dict(data_class=GeodesignhubProjectCenter, data=c.json())
        return center

    def download_design_data_from_geodesignhub(
        self,
    ) -> Union[ErrorResponse, FeatureCollection]:
        
        """
        Downloads design data from Geodesignhub for a specified team and synthesis.
        This method uses the API helper to retrieve synthesis data based on the provided
        team and synthesis IDs. If the API call is unsuccessful (i.e., status code is not 200),
        it returns an ErrorResponse indicating that one or more required identifiers were not found.
        On success, it returns the design details as a FeatureCollection.
        Returns:
            Union[ErrorResponse, FeatureCollection]: An ErrorResponse if the API call fails,
            otherwise the design details as a FeatureCollection.
        """
        r = self.api_helper.get_single_synthesis(
            teamid=int(self.cteam_id), synthesisid=self.synthesis_id
        )

        try:
            assert r.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return error_msg

        _design_details_raw = r.json()

        return _design_details_raw

    def process_design_data_from_geodesignhub(
        self, unprocessed_design_geojson
    ) -> Union[ErrorResponse, FeatureCollection]:
        
        """
        Processes unprocessed design GeoJSON data from Geodesignhub and converts it into a FeatureCollection
        with enriched properties and appropriate geometry types.
        Args:
            unprocessed_design_geojson (dict): A GeoJSON-like dictionary containing design features from Geodesignhub.
        Returns:
            Union[ErrorResponse, FeatureCollection]: Returns a FeatureCollection of processed features if successful,
            or an ErrorResponse if an unsupported geometry type is encountered.
        Workflow:
            - Iterates through each feature in the input GeoJSON.
            - Populates default building data (height, base_height) if not available.
            - Assigns unique building IDs and diagram IDs.
            - Converts feature properties to GeodesignhubDesignFeatureProperties dataclass.
            - For "policy" areatype, generates a point grid and creates features with zero height.
            - For other types, processes geometry as Polygon, LineString, or buffered Point.
            - Returns an error if geometry type is unsupported.
            - Collects all processed features into a FeatureCollection and returns it.
        """
        _all_features: List[Feature] = []

        my_geometry_helper = GeometryHelper()
        # Populate Default building data if not available
        for _single_diagram_feature in unprocessed_design_geojson["features"]:
            _diagram_properties = _single_diagram_feature["properties"]
            _project_or_policy = _diagram_properties["areatype"]
            _diagram_properties["height"] = (
                6
                if _diagram_properties["volume_information"]["max_height"] == 0
                else _diagram_properties["volume_information"]["max_height"]
            )
            _diagram_properties["base_height"] = (
                0
                if _diagram_properties["volume_information"]["min_height"] == 0
                else _diagram_properties["volume_information"]["min_height"]
            )
            _diagram_properties["diagram_id"] = _diagram_properties["diagramid"]
            _diagram_properties["building_id"] = str(uuid.uuid4())
            _feature_properties = from_dict(
                data_class=GeodesignhubDesignFeatureProperties, data=_diagram_properties
            )

            if _project_or_policy == "policy":
                point_grid = my_geometry_helper.create_point_grid(
                    geojson_feature=_single_diagram_feature
                )
                _feature_properties.height = 0
                _feature_properties.base_height = 0
                for _point_feature in point_grid["features"]:
                    _point_geometry = Polygon(
                        coordinates=_point_feature["geometry"]["coordinates"]
                    )
                    _feature = Feature(
                        geometry=_point_geometry, properties=asdict(_feature_properties)
                    )
                    _all_features.append(_feature)
            else:
                # We assume that GDH will provide a polygon
                if _single_diagram_feature["geometry"]["type"] == "Polygon":
                    _geometry = Polygon(
                        coordinates=_single_diagram_feature["geometry"]["coordinates"]
                    )
                elif _single_diagram_feature["geometry"]["type"] == "LineString":
                    _geometry = LineString(
                        coordinates=_single_diagram_feature["geometry"]["coordinates"]
                    )
                elif _single_diagram_feature["geometry"]["type"] == "Point":
                    point = shape(_single_diagram_feature["geometry"])
                    buffered_point = point.buffer(0.00005)
                    buffered_polygon = export_to_json(buffered_point)
                    _geometry = Polygon(coordinates=buffered_polygon["coordinates"])
                    # Buffer the point

                else:
                    error_msg = ErrorResponse(
                        status=0,
                        message="Building shadows can only be computed for polygon features, you are trying to compute shadows for .",
                        code=400,
                    )
                    return error_msg
                _feature = Feature(
                    geometry=_geometry, properties=asdict(_feature_properties)
                )
                _all_features.append(_feature)

        _diagram_feature_collection = FeatureCollection(features=_all_features)

        return _diagram_feature_collection

    def download_diagram_data_from_geodesignhub(
        self,
    ) -> Union[ErrorResponse, FeatureCollection]:
        my_api_helper = GeodesignHub.GeodesignHubClient(
            url=config.apisettings["serviceurl"],
            project_id=self.project_id,
            token=self.apitoken,
        )
        # Download Data
        d = my_api_helper.get_single_diagram(diagid=self.diagram_id)

        try:
            assert d.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return error_msg

        _diagram_details_raw = d.json()
        # Populate Default building data if not available
        if not bool(_diagram_details_raw["building_data"]):
            _default_building_data = {
                "meters_above_ground": 10,
                "meters_below_ground": 0,
            }
        else:
            _default_building_data = _diagram_details_raw["building_data"]

        _diagram_details_feature_collection = _diagram_details_raw["geojson"]

        _all_features: List[Feature] = []
        for f in _diagram_details_feature_collection["features"]:
            _f_props = f["properties"]
            _building_data = BuildingData(
                height=_default_building_data["meters_above_ground"],
                base_height=_default_building_data["meters_below_ground"],
            )

            _diagram_details_raw["height"] = asdict(_building_data)["height"]
            _diagram_details_raw["base_height"] = asdict(_building_data)["base_height"]
            _diagram_details_raw["diagram_id"] = self.diagram_id
            _diagram_details_raw["building_id"] = str(uuid.uuid4())
            _diagram_details_raw["color"] = _f_props["color"]
            _feature_properties = from_dict(
                data_class=GeodesignhubFeatureProperties, data=_diagram_details_raw
            )

            # We assume that GDH will provide a polygon
            if f["geometry"]["type"] == "Polygon":
                _geometry = Polygon(coordinates=f["geometry"]["coordinates"])
            elif f["geometry"]["type"] == "LineString":
                _geometry = LineString(coordinates=f["geometry"]["coordinates"])
            else:
                error_msg = ErrorResponse(
                    status=0,
                    message="Building shadows can only be computed for polygon features, you are trying to compute shadows for .",
                    code=400,
                )
                return None
            _feature = Feature(
                geometry=_geometry, properties=asdict(_feature_properties)
            )
            _all_features.append(_feature)

        _diagram_feature_collection = FeatureCollection(features=_all_features)

        return _diagram_feature_collection

    def generate_tree_point_feature_collection(
        self, point_feature_list
    ) -> FeatureCollection:
        _all_tree_features: List[Feature] = []
        for point_feature in point_feature_list:
            _geometry = Point(coordinates=point_feature["geometry"]["coordinates"])
            _feature = Feature(geometry=_geometry, properties={})
            _all_tree_features.append(_feature)

        _trees_feature_collection = FeatureCollection(features=_all_tree_features)

        return _trees_feature_collection

    def filter_design_tree_points(
        self, unprocessed_design_geojson: FeatureCollection
    ) -> FeatureCollection:
        # This method filters the tree points out of a design Geojson

        _all_tree_features: List[Feature] = []
        # Populate Default building data if not available
        for f in unprocessed_design_geojson["features"]:
            if f["geometry"]["type"] in ["Point"]:
                _geometry = Point(coordinates=f["geometry"]["coordinates"])
                _diagram_properties = f["properties"]
                _tree_feature_properties = TreeFeatureProperties(
                    author=_diagram_properties["author"],
                    description=_diagram_properties["description"],
                )
                # _feature_properties = from_dict(
                #     data_class=GeodesignhubDesignFeatureProperties, data=_diagram_properties
                # )
                _feature = Feature(
                    geometry=_geometry, properties=asdict(_tree_feature_properties)
                )
                _all_tree_features.append(_feature)

        _trees_feature_collection = FeatureCollection(features=_all_tree_features)

        return _trees_feature_collection

    def filter_to_get_gi_system(
        self, geodesignhub_project_data: GeodesignhubProjectData
    ) -> int:
        geodesignhub_project_data = asdict(geodesignhub_project_data)
        interesting_system = [
            d
            for d in geodesignhub_project_data["systems"]
            if d["name"].lower() in ["tree", "gi"]
        ]
        return interesting_system[0]["id"]

    def download_project_data_from_geodesignhub(
        self,
    ) -> Union[ErrorResponse, GeodesignhubProjectData]:
        my_api_helper = GeodesignHub.GeodesignHubClient(
            url=config.apisettings["serviceurl"],
            project_id=self.project_id,
            token=self.apitoken,
        )
        # Download Data
        s = my_api_helper.get_all_systems()
        b = my_api_helper.get_project_bounds()
        c = my_api_helper.get_project_center()
        t = my_api_helper.get_project_tags()

        # Check responses / data
        try:
            assert s.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return error_msg

        systems = s.json()
        all_systems: List[GeodesignhubSystem] = []
        all_system_details: List[GeodesignhubSystemDetail] = []
        for s in systems:
            current_system = from_dict(data_class=GeodesignhubSystem, data=s)
            sd = my_api_helper.get_single_system(system_id=current_system.id)
            sd_raw = sd.json()
            current_system_details = from_dict(
                data_class=GeodesignhubSystemDetail, data=sd_raw
            )
            all_system_details.append(current_system_details)
            all_systems.append(current_system)

        try:
            assert b.status_code == 200
        except AssertionError:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return error_msg

        center = from_dict(data_class=GeodesignhubProjectCenter, data=c.json())
        bounds = from_dict(data_class=GeodesignhubProjectBounds, data=b.json())
        tags = from_dict(data_class=GeodesignhubProjectTags, data={"tags": t.json()})
        project_data = GeodesignhubProjectData(
            systems=all_systems,
            system_details=all_system_details,
            bounds=bounds,
            center=center,
            tags=tags,
        )

        return project_data


class ShadowComputationHelper:
    """
    A helper class to compute shadows for Geodesignhub (GDH) buildings and existing roads.
    Attributes:
        session_id (str): Unique identifier for the session.
        shadow_date_time (str): The timestamp for which the shadow computation is performed.
        bounds (str): The geographical bounds for the computation.
        project_id (str): The project identifier.
        gdh_geojson (dict, optional): GeoJSON data for the design diagram buildings.
    Methods:
        compute_gdh_buildings_shadow():
            Computes shadows for GDH buildings and existing roads. This involves downloading
            road data, generating shadows for GDH buildings, and calculating intersections
            between shadows and roads. The method uses a queueing system to manage tasks
            and dependencies.
    """

    def __init__(
        self,
        session_id: str,
        shadow_date_time: str,
        bounds: str,
        project_id: str,
        design_diagram_geojson=None,
    ):
        self.gdh_geojson = design_diagram_geojson
        self.session_id = session_id
        self.shadow_date_time = shadow_date_time
        self.bounds = bounds
        self.project_id = project_id

    def compute_gdh_buildings_shadow(self):
        """This method computes the shadow for existing or GDH buidlings"""
        my_url_generator = ViewDataGenerator(view_type=None, project_id=self.project_id)
        r_url = my_url_generator.get_existing_roads_geojson_url()

        hash_of_timestamp = str(
            int(
                hashlib.sha256(self.shadow_date_time.encode("utf-8")).hexdigest(),
                16,
            )
            % 10**8
        )
        if r_url:
            # first download the trees and then compute design shadow

            roads_download_job = RoadsDownloadRequest(
                bounds=self.bounds,
                session_id=str(self.session_id),
                request_date_time=self.shadow_date_time,
                roads_url=r_url.url,
            )

            roads_download_result = q.enqueue(
                utils.download_roads,
                asdict(roads_download_job),
                on_success=notify_roads_download_complete,
                on_failure=notify_roads_download_failure,
                job_id=self.session_id + "@" + hash_of_timestamp + "@roads",
            )
            
            gdh_buildings_shadow_dependency = Dependency(
                jobs=[roads_download_result], allow_failure=False, enqueue_at_front=True
            )

            # generate the GDH Shadows
            gdh_worker_data = GeodesignhubDataShadowGenerationRequest(
                buildings=self.gdh_geojson,
                session_id=self.session_id,
                request_date_time=self.shadow_date_time,
                bounds=self.bounds,
            )
            shadow_canpopy_job_id = self.session_id + "@" + hash_of_timestamp
            
            gdh_shadow_result = q.enqueue(
                utils.compute_gdh_shadow_with_tree_canopy,
                asdict(gdh_worker_data),
                on_success=notify_shadow_complete,
                on_failure=shadow_generation_failure,
                job_id=shadow_canpopy_job_id,
                depends_on=gdh_buildings_shadow_dependency,
            )

            _gdh_roads_shadows_start_processing = RoadsShadowsComputationStartRequest(
                bounds=self.bounds,
                session_id=self.session_id,
                request_date_time=self.shadow_date_time,
            )

            gdh_roads_intersection_result = q.enqueue(
                utils.kickoff_gdh_roads_shadows_stats,
                asdict(_gdh_roads_shadows_start_processing),
                on_success=notify_gdh_roads_shadow_intersection_complete,
                on_failure=notify_gdh_roads_shadow_intersection_failure,
                job_id=self.session_id + "@gdh_roads_shadow",
                depends_on=[gdh_shadow_result],
            )
        else:
            logger.error(
                "Roads URL not found, existing Roads as GeoJSON must be present to compute shadows"
            )
