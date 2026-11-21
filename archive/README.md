# Archive

This directory holds code that has been retired from the live application but is
kept in the repository for reference. Archived files are not imported by the
running app and have no effect on runtime behavior.

## Contents

- `templates/diagram_shadow.html` — retired Jinja2 template for the
  `/diagram_shadow/` diagram-level shadow analysis view.
- `views/diagram_shadow_views.py` — retired Flask view
  (`generate_diagram_shadow`) that rendered `diagram_shadow.html`.

## Archived

- Date: 2026-11-21
- Reason: The diagram-level shadow analysis view was superseded by the
  design-level `/design_shadow/` view (`design_shadow.html`). The
  `/diagram_shadow/` route and its template were removed from the live app;
  shared infrastructure (the `/gdh_generated_shadow` and
  `/get_shadow_roads_stats` routes, `ShadowComputationHelper`, and the
  `tree_shadow_analysis` layer config) remains in use by other views and was
  intentionally left untouched.
