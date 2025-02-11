#!/usr/bin/env python3
from flask import render_template
from flask import request, Response
from flask import session, redirect, url_for
from conn import get_redis
from dotenv import load_dotenv, find_dotenv
from dashboard import create_app
from dashboard.configurations.data_helper import ViewDataGenerator
import json
from rq import Queue
from worker import conn
from dataclasses import asdict
from data_definitions import (
    COGDataSourceList,
    ErrorResponse,
    FGBDataSourceList,
    GeodesignhubDiagramGeoJSON,
    PMTilesDataSourceList,
    ShadowViewSuccessResponse,
    RoadsShadowOverlap,
    ToolboxDesignViewDetails,
    ToolboxDiagramViewDetails,
    FloodingViewSuccessResponse,
    DrawViewSuccessResponse,
    ToolboxDrawDiagramViewDetails,
    DiagramUploadDetails,
    WMSDataSourceList,
)
from flask import render_template, redirect, url_for
from flask_bootstrap import Bootstrap5
from typing import List
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length
from wtforms.validators import DataRequired
import os
from download_helper import (
    GeodesignhubDataDownloader,
    ShadowComputationHelper,
    
    kickoff_drawn_trees_shadow_job,
)
import arrow
import uuid
import geojson
from flask_sqlalchemy import SQLAlchemy
import logging

logger = logging.getLogger("local-climate-response")


load_dotenv(find_dotenv())
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
base_dir = os.path.abspath(os.path.dirname(__file__))
redis = get_redis()
q = Queue(connection=conn)

MIMETYPE = "application/json"


def get_locale():
    # if the user has set up the language manually it will be stored in the session,
    # so we use the locale from the user settings
    try:
        language = session["language"]
    except KeyError:
        language = None
    if language is not None:
        return language
    return request.accept_languages.best_match(app.config["LANGUAGES"].keys())


app, babel = create_app()
app.secret_key = os.getenv("SECRET_KEY", "My Secret key")
app.config["BABEL_TRANSLATION_DIRECTORIES"] = os.path.join(base_dir, "translations")
babel.init_app(app, locale_selector=get_locale)

csrf = CSRFProtect(app)
bootstrap = Bootstrap5(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



@app.route("/", methods=["GET"])
def home():
    return render_template("home.html",op={})


@app.context_processor
def inject_conf_var():
    return dict(
        AVAILABLE_LANGUAGES=app.config["LANGUAGES"],
        CURRENT_LANGUAGE=session.get(
            "language",
            request.accept_languages.best_match(app.config["LANGUAGES"].keys()),
        ),
    )


@app.route("/language/<language>")
def set_language(language=None):
    session["language"] = language
    return redirect(request.referrer)


@app.route("/gdh_generated_shadow", methods=["GET"])
def get_diagram_shadow():
    shadow_key = request.args.get("shadow_key", "0")

    shadow_exists = redis.exists(shadow_key)
    if shadow_exists:
        s = redis.get(shadow_key)
        shadow = json.loads(s)
    else:
        shadow = json.dumps({"type": "FeatureCollection", "features": []})
    
    return Response(shadow, status=200, mimetype=MIMETYPE)






@app.route("/get_shadow_roads_stats", methods=["GET"])
def generate_shadow_road_stats():
    roads_shadow_stats_key = request.args.get("roads_shadow_stats_key", "0")

    roads_shadow_stats_exists = redis.exists(roads_shadow_stats_key)

    if roads_shadow_stats_exists:
        s = redis.get(roads_shadow_stats_key)
        shadow_stats = json.loads(s)
    else:
        default_shadow = RoadsShadowOverlap(
            total_roads_kms=0.0, shadowed_kms=0.0, job_id="0000", total_shadow_area=0.0
        )
        shadow_stats = asdict(default_shadow)
    return Response(json.dumps(shadow_stats), status=200, mimetype=MIMETYPE)


@app.route("/design_flooding_analysis/", methods=["GET"])
def generate_design_flooding_analysis():
    try:
        projectid = request.args.get("projectid")
        apitoken = request.args.get("apitoken")
        synthesisid = request.args.get("synthesisid")
        cteamid = request.args.get("cteamid")

    except KeyError:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Design Team ID / Design ID or API Token ID. One or more of these were not found in your request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)
    design_view_details = ToolboxDesignViewDetails(
        project_id=projectid,
        cteam_id=cteamid,
        synthesis_id=synthesisid,
        api_token=apitoken,
        view_type="flood",
    )

    if projectid and cteamid and apitoken and synthesisid:
        session_id = uuid.uuid4()
        my_geodesignhub_downloader = GeodesignhubDataDownloader(
            session_id=session_id,
            project_id=projectid,
            synthesis_id=synthesisid,
            cteam_id=cteamid,
            apitoken=apitoken,
        )

    project_data = my_geodesignhub_downloader.download_project_data_from_geodesignhub()
    if not project_data:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)

    _design_feature_collection = (
        my_geodesignhub_downloader.download_design_data_from_geodesignhub()
    )
    gj_serialized = json.loads(geojson.dumps(_design_feature_collection))

    design_geojson = GeodesignhubDiagramGeoJSON(geojson=gj_serialized)

    maptiler_key = os.getenv("maptiler_key", "00000000000000")

    success_response = FloodingViewSuccessResponse(
        status=1,
        message="Data from Geodesignhub retrieved",
        geometry_data=design_geojson,
        project_data=project_data,
        maptiler_key=maptiler_key,
        session_id=str(session_id),
        view_details=design_view_details,
    )

    return render_template("design_flooding_analysis.html", op=asdict(success_response))


class DiagramUploadForm(FlaskForm):
    diagram_name = StringField(label=("Name your diagram"), validators=[DataRequired()])
    drawn_geojson = HiddenField()
    project_id = HiddenField()
    apitoken = HiddenField()
    gi_system_id = HiddenField()
    submit = SubmitField()


@app.route("/diagram_upload_result/", methods=["GET"])
def redirect_upload_diagram():

    status = int(request.args.get("status"))
    apitoken = request.args["apitoken"]
    project_id = request.args["project_id"]
    message = (
        "Diagram successfully created"
        if status
        else "Error in creating a diagram, please contact your administrator"
    )
    return render_template(
        "add_diagram/diagram_add_status.html",
        op=status,
        message=message,
        apitoken=apitoken,
        project_id=project_id,
    )


@app.route("/design_shadow/", methods=["GET"])
def generate_design_shadow():
    try:
        projectid = request.args.get("projectid")
        apitoken = request.args.get("apitoken")
        synthesisid = request.args.get("synthesisid")
        cteamid = request.args.get("cteamid")

    except KeyError:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Design Team ID / Design ID or API Token ID. One or more of these were not found in your request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)

    design_view_details = ToolboxDesignViewDetails(
        project_id=projectid,
        cteam_id=cteamid,
        synthesis_id=synthesisid,
        api_token=apitoken,
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
        august_6_date = f"{current_year}-08-06T10:10:00"
        shadow_date_time = august_6_date

    my_view_helper = ViewDataGenerator(
        view_type="tree_shadow_analysis", project_id=projectid
    )

    fgb_layers: FGBDataSourceList = my_view_helper.generate_fgb_layers_list()
    cog_layers: COGDataSourceList = my_view_helper.generate_cog_layers_list()
    pmtiles_layers: PMTilesDataSourceList = my_view_helper.generate_pmtiles_layers_list()
    wms_layers: WMSDataSourceList = my_view_helper.generate_wms_layers_list()

    session_id = uuid.uuid4()
    my_geodesignhub_downloader = GeodesignhubDataDownloader(
        session_id=session_id,
        project_id=projectid,
        synthesis_id=synthesisid,
        cteam_id=cteamid,
        apitoken=apitoken,
    )

    project_data = my_geodesignhub_downloader.download_project_data_from_geodesignhub()
    if not project_data:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)

    _unprocessed_design_geojson = (
        my_geodesignhub_downloader.download_design_data_from_geodesignhub()
    )

    _design_feature_collection = (
        my_geodesignhub_downloader.process_design_data_from_geodesignhub(
            unprocessed_design_geojson=_unprocessed_design_geojson
        )
    )
    gj_serialized = json.loads(geojson.dumps(_design_feature_collection))

    design_geojson = GeodesignhubDiagramGeoJSON(geojson=gj_serialized)

    _design_trees_feature_collection = (
        my_geodesignhub_downloader.filter_design_tree_points(
            unprocessed_design_geojson=_unprocessed_design_geojson
        )
    )
    tree_fc_serialized = json.loads(geojson.dumps(_design_trees_feature_collection))
    trees_feature_collection = GeodesignhubDiagramGeoJSON(geojson=tree_fc_serialized)

    shadow_computation_helper = ShadowComputationHelper(
        session_id=str(session_id),
        design_diagram_geojson=gj_serialized,
        shadow_date_time=shadow_date_time,
        bounds=project_data.bounds.bounds,
        project_id=projectid,
    )
    shadow_computation_helper.compute_gdh_buildings_shadow()

    # Download Data
    maptiler_key = os.getenv("maptiler_key", "00000000000000")
    
    success_response = ShadowViewSuccessResponse(
        status=1,
        message="Data from Geodesignhub retrieved",
        geometry_data=design_geojson,
        trees_feature_collection=trees_feature_collection,
        project_data=project_data,
        maptiler_key=maptiler_key,
        session_id=str(session_id),
        shadow_date_time=shadow_date_time,
        view_details=design_view_details,
        wms_layers=wms_layers.layers,
        cog_layers=cog_layers.layers,
        pmtiles_layers=pmtiles_layers.layers,
        fgb_layers=fgb_layers.layers,
    )
    return render_template("design_shadow.html", op=asdict(success_response))


@app.route("/get_drawn_trees_shadows", methods=["GET"])
def get_drawn_trees_shadows():
    trees_key = request.args.get("drawn_trees_shadows_key", "0")
    
    trees_session_exists = redis.exists(trees_key) 

    if trees_session_exists:
        trees_data_raw = redis.get(trees_key)
        trees = json.loads(trees_data_raw.decode("utf-8"))
    else:
        trees = {"type": "FeatureCollection", "features": []}

    trs = json.dumps(trees)

    return Response(trs, status=200, mimetype=MIMETYPE)


@app.route("/generate_drawn_trees_shadow/", methods=["POST"])
def generate_drawn_trees_shadow():
    geojson_payload = request.get_json()

    unprocessed_tree_geojson = geojson_payload["unprocessed_tree_geojson"]
    session_id = request.args.get("session_id")
    state_id = request.args.get("state_id")
    kickoff_drawn_trees_shadow_job(
        unprocessed_drawn_trees=unprocessed_tree_geojson, session_id=session_id, state_id=state_id
    )

    return Response({}, status=200, mimetype=MIMETYPE)


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


@app.route("/draw_trees/", methods=["GET", "POST"])
def draw_trees_view():
    session_id = uuid.uuid4()
    try:
        projectid = request.args.get("projectid")
        apitoken = request.args.get("apitoken")
    except KeyError:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)

    maptiler_key = os.getenv("maptiler_key", "00000000000000")

    my_geodesignhub_downloader = GeodesignhubDataDownloader(
        session_id=session_id,
        project_id=projectid,
        apitoken=apitoken,
    )
    draw_view_details = ToolboxDrawDiagramViewDetails(
        api_token=apitoken,
        project_id=projectid,
        view_type="draw",
    )

    my_view_helper = ViewDataGenerator(
        view_type="tree_shadow_analysis", project_id=projectid
    )

    fgb_layers: FGBDataSourceList = my_view_helper.generate_fgb_layers_list()
    cog_layers: COGDataSourceList = my_view_helper.generate_cog_layers_list()
    pmtiles_layers: PMTilesDataSourceList = my_view_helper.generate_pmtiles_layers_list()
    wms_layers: WMSDataSourceList = my_view_helper.generate_wms_layers_list()

    project_data = my_geodesignhub_downloader.download_project_data_from_geodesignhub()
    if not project_data:
        error_msg = ErrorResponse(
            status=0,
            message="Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request.",
            code=400,
        )
        return Response(asdict(error_msg), status=400, mimetype=MIMETYPE)
    gi_system_id = my_geodesignhub_downloader.filter_to_get_gi_system(
        geodesignhub_project_data=project_data
    )
    diagram_upload_form = DiagramUploadForm(
        project_id=projectid, apitoken=apitoken, gi_system_id=gi_system_id
    )
    

    if diagram_upload_form.validate_on_submit():
        diagram_upload_form_data = diagram_upload_form.data
        point_feature_list = diagram_upload_form_data["drawn_geojson"]
        gi_system_id = diagram_upload_form_data["gi_system_id"]
        diagram_name = diagram_upload_form_data["diagram_name"]
        project_id = diagram_upload_form_data["project_id"]
        apitoken = diagram_upload_form_data["apitoken"]

        my_geodesignhub_downloader = GeodesignhubDataDownloader(
            session_id=str(session_id), project_id=project_id, apitoken=apitoken
        )
        _design_trees_feature_collection = (
            my_geodesignhub_downloader.generate_tree_point_feature_collection(
                point_feature_list=json.loads(point_feature_list)
            )
        )
        diagram_details = DiagramUploadDetails(
            geometry=geojson.dumps(_design_trees_feature_collection),
            project_or_policy="project",
            feature_type="polygon",
            description=diagram_name,
            funding_type="pu",
            sys_id=gi_system_id,
        )
        upload_response = my_geodesignhub_downloader.upload_diagram(
            diagram_upload_details=diagram_details
        )
        upload_response_dict = asdict(upload_response)
        return redirect(
            url_for(
                "redirect_upload_diagram",
                apitoken=apitoken,
                project_id=project_id,
                status=upload_response_dict["status"],
                code=307,
            )
        )

    success_response = DrawViewSuccessResponse(
        status=1,
        message="Data from Geodesignhub retrieved",
        project_data=project_data,
        maptiler_key=maptiler_key,
        session_id=str(session_id),
        wms_layers=wms_layers.layers,
        cog_layers=cog_layers.layers,
        fgb_layers=fgb_layers.layers,
        pmtiles_layers=pmtiles_layers.layers,
        view_details=draw_view_details,
        apitoken=apitoken,
        project_id=projectid,
    )
    
    return render_template(
        "add_diagram/draw_trees.html",
        op=asdict(success_response),
        form=diagram_upload_form,
    )


if __name__ == "__main__":
    app.debug = True
    port = int(os.environ.get("PORT", 8001))
    app.run(port=port)
