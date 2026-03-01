from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class Contact:
    website: str


@dataclass
class APIVersion:
    version: float


@dataclass
class ImpactIntensity:
    intensity: str


@dataclass
class ImpactUnit:
    unit: str
    description: str


@dataclass
class ImpactBase:
    magnitude: float
    unit: ImpactUnit
    intensity: ImpactIntensity


# ---------------------------------------------------------------------------
# v2 schemas
# ---------------------------------------------------------------------------

@dataclass
class StylingProperties:
    color: str = "#3388ff"
    hidden: bool = False


@dataclass
class PhysicalProperties:
    default_inflow: Optional[float] = None
    default_depth: Optional[float] = None
    default_width: Optional[float] = None
    default_radius: Optional[float] = None
    area_inflow: Optional[float] = None
    area_depth: Optional[float] = None
    area_width: Optional[float] = None
    area_radius: Optional[float] = None


@dataclass
class SpecializedImpacts:
    climate: Optional[Any] = None
    water_quality: Optional[Any] = None
    cost: Optional[Any] = None


@dataclass
class EnhancedImpactBase:
    magnitude: float
    unit: ImpactUnit
    intensity: ImpactIntensity
    specialized: Optional[SpecializedImpacts] = None


@dataclass
class NatureBasedSolutionV2Read:
    name: str
    definition: str
    cobenefits: str
    specificdetails: str
    id: int
    geometry: Optional[Any] = None
    styling: Optional[StylingProperties] = None
    physical_properties: Optional[PhysicalProperties] = None
    area: Optional[float] = None
    length: Optional[float] = None
    measure_id: Optional[str] = None
    impacts: Optional[List[ImpactBase]] = None


@dataclass
class NatureBasedSolutionFeature:
    type: str = "Feature"
    geometry: Optional[Any] = None
    properties: Optional[Any] = None


@dataclass
class MeasureTypeRead:
    id: str
    name: str
    description: Optional[str] = None
    default_color: Optional[str] = None
    default_inflow: Optional[float] = None
    default_depth: Optional[float] = None
    default_width: Optional[float] = None
    default_radius: Optional[float] = None


@dataclass
class MapSettingsRead:
    center: Optional[List[float]] = None
    zoom: Optional[int] = None
    base_layer: Optional[str] = None


@dataclass
class ProjectRead:
    title: str
    id: str
    description: Optional[str] = None
    settings: Optional[dict] = None
    map: Optional[MapSettingsRead] = None
    targets: Optional[dict] = None
    areas: Optional[List[Any]] = None
