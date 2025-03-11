
from sqlalchemy.orm import declarative_base
from dashboard import db

Base = db.Model  # model base class
from .adaptation_target import AdaptationTarget
from .apiversion import ApiVersion
from .impact import Impact
from .impact_intensity import ImpactIntensity
from .impact_unit import ImpactUnit
from .naturebasedsolution import Association, NatureBasedSolution
