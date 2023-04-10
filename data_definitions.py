from dataclasses import dataclass
from typing import List
from typing import Optional

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
class GeodesignhubFeatureProperties:
    sysid: int    
    description: str    
    height: float
    base_height: float
    color:str
    diagram_id:int
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
    # Source: https://www.geodesignhub.com/api/#systems-api-systems-collection-get
    bounds: str

@dataclass
class GeodesignhubProjectData:
    systems: List[GeodesignhubSystem]
    bounds: GeodesignhubProjectBounds

@dataclass
class DiagramShadowSuccessResponse:
    message: str
    status: int
    project_data: GeodesignhubProjectData
    diagram_geojson: GeodesignhubDiagramGeoJSON
    maptiler_key: str

@dataclass
class ShadowGenerationRequest:
    geojson: dict
    date_time: str