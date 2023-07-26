from dataclasses import dataclass
from typing import List, Optional, Union

@dataclass
class ErrorResponse:
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
    color:str
    diagram_id:int
    building_id: str

@dataclass
class RoadsShadowsComputationStartRequest:
    bounds: str
    session_id: str
    request_date_time: str


@dataclass
class GeodesignhubDesignFeatureProperties:
    author:str
    description: str    
    height: float
    base_height: float
    color:str
    diagram_id:int
    building_id: str
    areatype:str
    min_height: float
    max_height:float
    tag_codes: str

@dataclass
class ExistingBuildingsFeatureProperties: 
    height: float
    base_height:float
    building_id: str

@dataclass
class GeodesignhubDiagramGeoJSON: 
    # Source: https://www.geodesignhub.com/api/#diagrams-api-diagram-detail-get
    geojson: dict
    

@dataclass
class GeodesignhubSystem:
    # Source: https://www.geodesignhub.com/api/#systems-api-systems-collection-get
    id:int
    sysname: str
    syscolor:str

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
class GeodesignhubProjectTags:
    
    tags: List[GeodesignhubProjectTag]


@dataclass
class GeodesignhubProjectCenter:    
    center: str

@dataclass
class GeodesignhubProjectData:
    systems: List[GeodesignhubSystem]
    bounds: GeodesignhubProjectBounds
    center: GeodesignhubProjectCenter
    tags: GeodesignhubProjectTags

@dataclass 
class ToolboxDesignViewDetails:
    api_token: str
    cteam_id: str
    synthesis_id: str
    project_id: str
    view_type:str

@dataclass 
class ToolboxDiagramViewDetails:
    api_token: str    
    diagram_id: str
    project_id: str

@dataclass
class ShadowViewSuccessResponse:
    message: str
    status: int
    project_data: GeodesignhubProjectData
    geometry_data: GeodesignhubDiagramGeoJSON
    maptiler_key: str
    session_id: str
    shadow_date_time:str
    baseline_index_wms_url:str
    trees_wms_url:str
    view_details: Union[ToolboxDesignViewDetails, ToolboxDiagramViewDetails]
    
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
    