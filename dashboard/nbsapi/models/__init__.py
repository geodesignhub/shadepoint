
from dashboard import db
Base = db.Model  # model base class

from .apiversion import ApiVersion  # noqa: E402, F401
from .impact import Impact  # noqa: E402, F401
from .impact_intensity import ImpactIntensity  # noqa: E402, F401
from .impact_unit import ImpactUnit  # noqa: E402, F401
from .measure_type import MeasureType  # noqa: E402, F401
from .naturebasedsolution import NatureBasedSolution  # noqa: E402, F401
from .project import Project, project_nbs_association  # noqa: E402, F401
from .specialized_impact import SpecializedImpact  # noqa: E402, F401
from .user import User  # noqa: E402, F401
