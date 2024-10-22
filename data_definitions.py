from dataclasses import dataclass
from typing import List, Union
from geojson import FeatureCollection
import enum


class GeometryType(str, enum.Enum):

    line = "line"
    point = "point"
    polygon = "polygon"


class RasterOrVector(str, enum.Enum):

    raster = "raster"
    vector = "vector"


@dataclass
class ErrorResponse:
    # A class to hold error resposnes
    message: str
    code: int
    status: int


@dataclass
class UploadSuccessResponse:
    # A class to hold error resposnes
    message: str
    code: int
    status: int


@dataclass
class BuildingData:
    height: float
    base_height: float


@dataclass
class TreeData:
    height: float
    base_height: float


@dataclass
class GeodesignhubFeatureProperties:
    sysid: int
    description: str
    height: float
    base_height: float
    color: str
    diagram_id: int
    building_id: str


@dataclass
class RoadsShadowsComputationStartRequest:
    bounds: str
    session_id: str
    request_date_time: str


@dataclass
class VolumeInformation:
    min_height: float
    max_height: float


@dataclass
class TreeFeatureProperties:
    author: str
    description: str


@dataclass
class DrawnTreesFeatureProperties:
    # Use building_id instead of tree_id
    height: float
    base_height: float
    building_id: str
    color: str


@dataclass
class GeodesignhubDesignFeatureProperties:
    author: str
    description: str
    height: float
    base_height: float
    color: str
    diagram_id: int
    building_id: str
    areatype: str
    volume_information: VolumeInformation
    tag_codes: str


@dataclass
class ExistingBuildingsFeatureProperties:
    height: float
    base_height: float
    building_id: str


@dataclass
class GeodesignhubDiagramGeoJSON:
    # Source: https://www.geodesignhub.com/api/#diagrams-api-diagram-detail-get
    geojson: FeatureCollection


@dataclass
class GeodesignhubSystem:
    # Source: https://www.geodesignhub.com/api/#systems-api-systems-collection-get
    id: int
    name: str
    color: str
    verbose_description: str


@dataclass
class GeodesignhubSystemDetail:
    id: int
    name: str
    color: str
    tag: str
    cost: int
    budget: int
    current_ha: float
    target_ha: float
    verbose_description: str


@dataclass
class AllSystemDetails:
    systems: List[GeodesignhubSystemDetail]


@dataclass
class GeodesignhubProjectBounds:

    bounds: str


@dataclass
class GeodesignhubProjectTag:
    id: str
    tag: str
    slug: str
    code: str
    diagrams: List[int]


@dataclass
class DiagramUploadDetails:
    geometry: FeatureCollection
    project_or_policy: str
    feature_type: str
    description: str
    funding_type: str
    sys_id: str


@dataclass
class GeodesignhubProjectTags:

    tags: List[GeodesignhubProjectTag]


@dataclass
class GeodesignhubProjectCenter:
    center: str


@dataclass
class GeodesignhubProjectData:
    systems: List[GeodesignhubSystem]
    system_details: List[GeodesignhubSystemDetail]
    bounds: GeodesignhubProjectBounds
    center: GeodesignhubProjectCenter
    tags: GeodesignhubProjectTags


@dataclass
class ToolboxDesignViewDetails:
    api_token: str
    cteam_id: str
    synthesis_id: str
    project_id: str
    view_type: str


@dataclass
class ToolboxDiagramViewDetails:
    api_token: str
    diagram_id: str
    project_id: str
    view_type: str


@dataclass
class ToolboxDrawDiagramViewDetails:
    api_token: str
    project_id: str
    view_type: str


@dataclass
class WMSLayer:
    url: str
    name: str
    dom_id: str


@dataclass
class WMSLayerList:
    layers: List[WMSLayer]


@dataclass
class COGLayer:
    url: str
    name: str
    dom_id: str


@dataclass
class PMTilesLayer:
    url: str
    name: str
    dom_id: str
    layer_type: RasterOrVector


@dataclass
class FGBLayer:
    url: str
    name: str
    dom_id: str
    color: str
    geometry_type: GeometryType


@dataclass
class COGLayerList:
    layers: List[COGLayer]

@dataclass
class ShadowViewSuccessResponse:
    message: str
    status: int
    project_data: GeodesignhubProjectData
    geometry_data: GeodesignhubDiagramGeoJSON
    trees_feature_collection: GeodesignhubDiagramGeoJSON
    maptiler_key: str
    session_id: str
    shadow_date_time: str
    cog_layers: List[COGLayer]
    wms_layers: List[WMSLayer]
    view_details: Union[ToolboxDesignViewDetails, ToolboxDiagramViewDetails]


@dataclass
class PMTilesLayerList:
    layers: List[PMTilesLayer]


@dataclass
class FGBLayerList:
    layers: List[FGBLayer]


@dataclass
class DrawViewSuccessResponse:
    message: str
    status: int
    project_data: GeodesignhubProjectData
    maptiler_key: str
    session_id: str
    view_details: ToolboxDrawDiagramViewDetails
    apitoken: str
    project_id: str
    wms_layers: WMSLayerList
    cog_layers: COGLayerList
    fgb_layers: FGBLayerList
    pmtiles_layers: PMTilesLayerList


@dataclass
class FloodingViewSuccessResponse:
    message: str
    session_id: str
    status: int
    project_data: GeodesignhubProjectData
    geometry_data: GeodesignhubDiagramGeoJSON
    maptiler_key: str
    flood_vulnerability_wms_url: str
    view_details: Union[ToolboxDesignViewDetails, ToolboxDiagramViewDetails]


@dataclass
class GeodesignhubDataShadowGenerationRequest:
    buildings: dict
    session_id: str
    request_date_time: str
    bounds: str


@dataclass
class DrawnTreesShadowGenerationRequest:
    trees: list
    session_id: str
    request_date_time: str
    processed_trees: dict


@dataclass
class ExistingBuildingsDataShadowGenerationRequest:
    session_id: str
    request_date_time: str
    bounds: str


@dataclass
class RoadsDownloadRequest:
    bounds: str
    session_id: str
    request_date_time: str
    roads_url: str


@dataclass
class TreesDownloadRequest:
    bounds: str
    session_id: str
    request_date_time: str
    trees_url: str


@dataclass
class BuildingsDownloadRequest:
    bounds: str
    session_id: str
    request_date_time: str
    buildings_url: str


@dataclass
class CanopyDownloadRequest:
    bounds: str
    session_id: str
    request_date_time: str
    canopy_url: str


@dataclass
class ShadowsRoadsIntersectionRequest:
    roads: str
    shadows: str
    job_id: str


@dataclass
class RoadsShadowOverlap:
    total_roads_kms: float
    shadowed_kms: float
    job_id: str
    total_shadow_area: float

@dataclass
class LayersAvailableInAllViews: 
    cogs: List[COGLayer]
    wms: List[WMSLayer]
    # TODO: Add FGB and PMtiles here
