"""Archived reference copy of the retired `/diagram_shadow/` Flask view.

This module is NOT imported by the running application. It is kept here only as
a historical record of the view that rendered `archive/templates/diagram_shadow.html`.

Originally lived in `app.py` as `generate_diagram_shadow()` and was removed on
2026-11-21 in favor of the design-level `/design_shadow/` view. Shared
infrastructure it depended on (the `/gdh_generated_shadow` and
`/get_shadow_roads_stats` routes, `ShadowComputationHelper`,
`ViewDataGenerator`, and the `tree_shadow_analysis` layer config) remains in
use by other views and was intentionally NOT archived.
"""

from dataclasses import asdict

import arrow
import geojson
import json
import os
import uuid

from flask import Response, request, render_template

from common import (
    ErrorResponse,
    GeodesignhubDataDownloader,
    GeodesignhubDiagramGeoJSON,
    ShadowViewSuccessResponse,
    ShadowComputationHelper,
    ToolboxDiagramViewDetails,
    ViewDataGenerator,
)

MIMETYPE = "application/json"


@app.route("/diagram_shadow/", methods=["GET"])
def generate_diagram_shadow():
    """This is the root of the web service, upon successful authentication a text will be displayed in the browser"""
    try:
        projectid = request.args.get("projectid")
        apitoken = request.args.get("apitoken")
        diagramid = request.args.get("diagramid")

    except KeyError:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)

    diagram_view_details = ToolboxDiagramViewDetails(
        api_token=apitoken,
        project_id=projectid,
        diagram_id=diagramid,
        view_type="shadow",
    )
    try:
        r_date_time = request.args.get("date_time", None)
        if not r_date_time:
            raise KeyError
        else:
            shadow_date_time = arrow.get(r_date_time).format("YYYY-MM-DDTHH:mm:ss")
    except KeyError:
        current_year = arrow.now().year
        august_6_date = "{year}-08-06T10:10:00".format(year=current_year)
        shadow_date_time = august_6_date

    if projectid and diagramid and apitoken:
        session_id = uuid.uuid4()
        # Initialize the API
        ## Download data from GDH
        my_geodesignhub_downloader = GeodesignhubDataDownloader(
            session_id=session_id,
            project_id=projectid,
            diagram_id=diagramid,
            apitoken=apitoken,
        )
        project_data = (
            my_geodesignhub_downloader.download_project_data_from_geodesignhub()
        )
        if not project_data:
            error_msg = ErrorResponse(
                status=0,
                message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
                code=400,
            )
            return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)
        else:
            _diagram_feature_collection = (
                my_geodesignhub_downloader.download_diagram_data_from_geodesignhub()
            )
            gj_serialized = json.loads(geojson.dumps(_diagram_feature_collection))
            diagram_geojson = GeodesignhubDiagramGeoJSON(geojson=gj_serialized)
            trees_feature_collection = GeodesignhubDiagramGeoJSON(
                geojson=json.loads(
                    json.dumps({"type": "FeatureCollection", "features": []})
                )
            )

            maptiler_key = os.getenv("maptiler_key", "00000000000000")
            my_view_helper = ViewDataGenerator(
                view_type="tree_shadow_analysis", project_id=projectid
            )
            wms_layers_list = my_view_helper.generate_wms_layers_list()
            cog_layers_list = my_view_helper.generate_cog_layers_list()
            pmtiles_layers_list = my_view_helper.generate_pmtiles_layers_list()
            fgb_layers_list = my_view_helper.generate_fgb_layers_list()
            shadow_computation_helper = ShadowComputationHelper(
                session_id=str(session_id),
                design_diagram_geojson=gj_serialized,
                shadow_date_time=shadow_date_time,
                bounds=project_data.bounds.bounds,
                project_id=projectid,
            )
            shadow_computation_helper.compute_gdh_buildings_shadow()

            success_response = ShadowViewSuccessResponse(
                status=1,
                message="Data from Geodesignhub retrieved",
                geometry_data=diagram_geojson,
                project_data=project_data,
                maptiler_key=maptiler_key,
                session_id=str(session_id),
                synthesis_id="",
                shadow_date_time=shadow_date_time,
                cog_layers=cog_layers_list.layers,
                wms_layers=wms_layers_list.layers,
                fgb_layers=fgb_layers_list.layers,
                pmtiles_layers=pmtiles_layers_list.layers,
                view_details=diagram_view_details,
                trees_feature_collection=trees_feature_collection,
            )

            return render_template("diagram_shadow.html", op=asdict(success_response))
    else:
        msg = ErrorResponse(
            status=0,
            message="Could download data from Geodesignhub, please check your project ID and API token.",
            code=400,
        )
        return Response(asdict(msg), status=400, mimetype=MIMETYPE)
