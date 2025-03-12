import json
from dashboard import create_app
from dashboard.nbsapi.data_definitions import NatureBasedSolutionRead


from dashboard.nbsapi.models.naturebasedsolution import NatureBasedSolution
from dashboard.nbsapi.models.adaptation_target import AdaptationTarget
from dashboard.nbsapi.models.impacts import Impact
from dashboard.nbsapi.models.impact_intensity import ImpactIntensity
from dashboard.nbsapi.models.impact_unit import ImpactUnit

from dacite import from_dict
from flask import Flask
import os
app = Flask(__name__)

@app.cli.command("initialize-db")
def initialize_db():
    app, db = create_app()
    with app.app_context():
        fixture_file_path = os.path.join(os.path.dirname(__file__), "nbs_definitions.json")
        
        
        with open(fixture_file_path, "r", encoding="utf-8") as f:
            all_nbs = json.load(f)

            for nbs in all_nbs:
                nbs_data = from_dict(data_class=NatureBasedSolutionRead, data=nbs)

                adaptation_targets = nbs_data.solution_targets
                for adatpation_target in adaptation_targets:
                    adaptation_target = AdaptationTarget(target=adatpation_target.adaptation.target)
                    db.session.add(adaptation_target)

                impacts = nbs_data.impacts
                for impact in impacts:
                    impact = Impact(magnitude=impact.magnitude)
                    impact_intensity = ImpactIntensity(intensity=impact.intensity.intensity, impact = impact)
                    impact_unit = ImpactUnit(unit=impact.unit.unit, dexcription=impact.unit.description, impacts = [impact])
                    db.session.add(impact)
                    db.session.add(impact_intensity)

                    db.session.add(impact_unit)

       
                # db.session.add(nbs)
            # db.session.commit()


if __name__ == "__main__":
    initialize_db()
