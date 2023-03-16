from dataclasses import dataclass
from typing import List
from geojson import FeatureCollection

@dataclass
class ErrorResponse:
    # A class to hold error resposnes
    message: str
    code: int
    status: int

@dataclass
class BuildingData:
    storeys_above_ground: int
    storeys_below_ground: int

@dataclass
class GeodesignhubDiagramProperties:     
    sysid: int
    rank:2
    description: str
    building_data: BuildingData


@dataclass
class GeodesignhubDiagramDetailShadow: 
    # Source: https://www.geodesignhub.com/api/#diagrams-api-diagram-detail-get
    geojson: FeatureCollection
    properties: GeodesignhubDiagramProperties

@dataclass
class GeodesignhubSystem:
    # Source: https://www.geodesignhub.com/api/#systems-api-systems-collection-get
    id:str
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
    status: int
    project_data: GeodesignhubProjectData
    diagram_data: GeodesignhubDiagramDetailShadow
