import arrow
import time
import pandas as pd
from data_definitions import (
    GeodesignhubDataShadowGenerationRequest,
    RoadsDownloadRequest,
    RoadsShadowOverlap,
    ShadowsRoadsIntersectionRequest,
    TreesDownloadRequest,
    RoadsShadowsComputationStartRequest,
    BuildingsDownloadRequest,
    ExistingBuildingsDataShadowGenerationRequest,
    ExistingBuildingsFeatureProperties,
    DrawnTreesShadowGenerationRequest,
    SiteEvaluationGenerationRequest,
    ErrorResponse,
    DrawnTreesFeatureProperties,
)
from typing import Union
import geojson
from dacite import from_dict
from pyproj import Geod
import geopandas as gpd
import pybdshadow


from shapely.geometry import LineString as ShapelyLineString
from shapely.geometry import MultiLineString as ShapelyMultiLineString

from shapely.geometry import shape
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box as ShapelyBox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import json
import tempfile
import uuid
from typing import List
import requests
import numpy as np
from dataclasses import asdict
from dashboard.conn import get_redis
from shapely import STRtree
import os
import hashlib
from geojson import Feature, FeatureCollection, Polygon, LineString, Point
from dotenv import load_dotenv, find_dotenv
import logging
from pyproj.exceptions import GeodError as GeodError

logger = logging.getLogger("local-climate-response")

load_dotenv(find_dotenv())
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
r = get_redis()


def _use_bounds_filtering() -> bool:
    """Parse USE_BOUNDS_FILTERING as a real boolean.

    ``os.getenv("USE_BOUNDS_FILTERING", None)`` treats "0" as truthy, which
    silently enables bounds filtering when the intent was to disable it.
    """
    return os.getenv("USE_BOUNDS_FILTERING", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def get_default_shadow_datetime():
    current_year = arrow.now().year
    august_6_date = "{year}-08-06T10:10:00".format(year=current_year)
    return august_6_date


def get_synthesis_shadow_key(synthesis_id: str, request_date_time: str) -> str:
    """Redis key for the shadow of a design.

    ``synthesis_id`` is the stable identifier of a Geodesignhub design, so the
    same design resolves to the same key on every request. This is what allows
    a final design's shadow to be reused instead of recomputed.
    """
    return f"{synthesis_id}:{request_date_time}_gdh_buildings_canopy_shadow"


def get_synthesis_roads_shadow_stats_key(
    synthesis_id: str, request_date_time: str
) -> str:
    """Redis key for the road/shadow overlap statistics of a design."""
    return f"{synthesis_id}:{request_date_time}_gdh_roads_shadow"


def _get_synthesis_id(request, session_id: str) -> str:
    """Return the stable synthesis id, falling back to the session id."""
    return getattr(request, "synthesis_id", None) or session_id


class DrawnTreesProcessor:
    def process_drawn_trees_data(
        self, unprocessed_tree_geojson
    ) -> Union[ErrorResponse, FeatureCollection]:
        """This method buffers the drawn trees GeoJSON as polygon and height"""

        my_geometry_helper = GeometryHelper()
        _all_features: List[Feature] = []
        buffered_tree_features = my_geometry_helper.buffer_tree_points(
            drawn_tree_geojson_features=unprocessed_tree_geojson
        )
        for _buffered_tree_feature in buffered_tree_features["features"]:
            _geometry = Polygon(
                coordinates=_buffered_tree_feature["geometry"]["coordinates"]
            )
            # We must use Building_id in the properties
            _feature_property = DrawnTreesFeatureProperties(
                height=10, base_height=0, color="#FF0000", building_id=str(uuid.uuid4())
            )
            _feature = Feature(geometry=_geometry, properties=asdict(_feature_property))
            _all_features.append(_feature)

        _drawn_trees_feature_collection = FeatureCollection(features=_all_features)

        return _drawn_trees_feature_collection


def download_roads(roads_download_request: RoadsDownloadRequest):
    _roads_download_request = from_dict(
        data_class=RoadsDownloadRequest, data=roads_download_request
    )
    bounds = _roads_download_request.bounds
    roads_url = _roads_download_request.roads_url
    session_roads_key = (
        _roads_download_request.session_id
        + ":"
        + _roads_download_request.request_date_time
        + ":"
        + "roads"
    )
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()

    empty_fc = {"type": "FeatureCollection", "features": []}
    roads_storage_key = bounds_hash[:15] + ":roads"
    r.set(session_roads_key, roads_storage_key)
    r.expire(session_roads_key, time=6000)

    if r.exists(roads_storage_key):
        fc_str = r.get(roads_storage_key)
        fc = json.loads(fc_str)
        # An empty FeatureCollection is treated as a failed download rather than
        # a valid cached result, so the next run retries instead of reusing it.
        if isinstance(fc, dict) and fc.get("features"):
            return fc

    bounds_filtering = _use_bounds_filtering()
    if bounds_filtering:
        # If bounds filtering is enabled, the bounds parameter in the URL is replaced with the current bounds
        r_url = roads_url.replace("__bounds__", bounds)
    else:
        r_url = roads_url

    try:
        download_request = requests.get(r_url, timeout=60)
    except requests.RequestException as exc:
        logger.error("Error downloading roads from %s: %s", r_url, exc)
        r.set(roads_storage_key, json.dumps(empty_fc), ex=300)
        return empty_fc

    if download_request.status_code == 200:
        try:
            fc = download_request.json()
        except ValueError:
            fc = None

        if not isinstance(fc, dict) or fc.get("type") != "FeatureCollection":
            logger.error(
                "Roads URL %s did not return a GeoJSON FeatureCollection",
                r_url,
            )
            r.set(roads_storage_key, json.dumps(empty_fc), ex=300)
            return empty_fc

        r.set(roads_storage_key, json.dumps(fc))
        r.expire(roads_storage_key, time=60000)
        return fc

    logger.error(
        "Error downloading roads from %s (HTTP %s); will retry on the next run",
        r_url,
        download_request.status_code,
    )
    # Cache the failure only briefly so a corrected URL/config recovers quickly.
    r.set(roads_storage_key, json.dumps(empty_fc), ex=300)
    return empty_fc


def download_trees(trees_download_request: TreesDownloadRequest):
    _trees_download_request = from_dict(
        data_class=TreesDownloadRequest, data=trees_download_request
    )
    bounds = _trees_download_request.bounds
    trees_url = _trees_download_request.trees_url
    session_trees_key = (
        f"{_trees_download_request.session_id}:"
        f"{_trees_download_request.request_date_time}:trees"
    )
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    trees_storage_key = f"{bounds_hash[:15]}:trees"

    r.set(session_trees_key, trees_storage_key)
    r.expire(session_trees_key, time=6000)

    fc = {"type": "FeatureCollection", "features": []}
    if r.exists(trees_storage_key):
        fc_str = r.get(trees_storage_key)
        fc = json.loads(fc_str)
    else:
        bounds_filtering = _use_bounds_filtering()
        t_url = (
            trees_url.replace("__bounds__", bounds) if bounds_filtering else trees_url
        )

        download_request = requests.get(t_url)
        if download_request.status_code == 200:
            fc = download_request.json()
            r.set(trees_storage_key, json.dumps(fc))
        else:
            logger.error("Error in setting downloaded trees to local memory")
            r.set(trees_storage_key, json.dumps(fc))
        r.expire(trees_storage_key, time=60000)

    return fc


def download_existing_buildings(buildings_download_request: BuildingsDownloadRequest):
    _buildings_download_request = from_dict(
        data_class=BuildingsDownloadRequest, data=buildings_download_request
    )
    bounds = _buildings_download_request.bounds
    buildings_url = _buildings_download_request.buildings_url
    session_key = (
        f"{_buildings_download_request.session_id}:"
        f"{_buildings_download_request.request_date_time}:"
        "existing_buildings"
    )
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    storage_key = f"{bounds_hash[:15]}:existing_buildings"

    r.set(session_key, storage_key)
    r.expire(session_key, time=6000)

    if r.exists(storage_key):
        fc_str = r.get(storage_key)
        fc = json.loads(fc_str)
    else:
        bounds_filtering = _use_bounds_filtering()
        b_url = (
            buildings_url.replace("__bounds__", bounds)
            if bounds_filtering
            else buildings_url
        )

        download_request = requests.get(b_url)
        if download_request.status_code == 200:
            fc = {"type": "FeatureCollection", "features": []}
            raw_fc = download_request.json()
            for f in raw_fc["features"]:
                new_prop = ExistingBuildingsFeatureProperties(
                    height=f["properties"]["max_height"],
                    base_height=0,
                    building_id=str(uuid.uuid4()),
                )
                f["properties"] = asdict(new_prop)
                fc["features"].append(f)
            r.set(storage_key, json.dumps(fc))
        else:
            logger.error("Error")
            r.set(
                storage_key, json.dumps({"type": "FeatureCollection", "features": []})
            )
        r.expire(storage_key, time=60000)

    return fc


class GeometryHelper:
    def buffer_tree_points(self, drawn_tree_geojson_features):
        df = gpd.GeoDataFrame.from_features(drawn_tree_geojson_features)
        df["geometry"] = df["geometry"].buffer(0.00005)
        point_json = df.to_json()
        buffered_point_gj = json.loads(point_json)

        return buffered_point_gj

    def create_point_grid(self, geojson_feature):
        """This function takes a policy polygon feature and generates a point grid"""

        x_spacing = 0.001  # The point spacing you want
        y_spacing = 0.001
        df = gpd.GeoDataFrame.from_features([geojson_feature])

        (
            xmin,
            ymin,
            xmax,
            ymax,
        ) = df.total_bounds  # Find the bounds of all polygons in the df
        xcoords = [c for c in np.arange(xmin, xmax, x_spacing)]  # Create x coordinates
        ycoords = [c for c in np.arange(ymin, ymax, y_spacing)]  # And y

        coordinate_pairs = np.array(np.meshgrid(xcoords, ycoords)).T.reshape(
            -1, 2
        )  # Create all combinations of xy coordinates
        geometries = gpd.points_from_xy(
            coordinate_pairs[:, 0], coordinate_pairs[:, 1]
        )  # Create a list of shapely points

        point_df = gpd.GeoDataFrame(
            geometry=geometries, crs=df.crs
        )  # Create the point df
        point_df["geometry"] = point_df["geometry"].buffer(0.00005)
        point_json = point_df.to_json()
        point_gj = json.loads(point_json)
        # TODO Filter the points to keep within bounds of the polygon
        # filtered_points = df.within(df.at[0,'geometry'])
        # logger.info(filtered_points)
        return point_gj


def kickoff_gdh_roads_shadows_stats(roads_shadow_computation_start):
    _roads_shadow_computation_details = from_dict(
        data_class=RoadsShadowsComputationStartRequest,
        data=roads_shadow_computation_start,
    )

    synthesis_id = _get_synthesis_id(
        _roads_shadow_computation_details,
        _roads_shadow_computation_details.session_id,
    )
    shadows_key = get_synthesis_shadow_key(
        synthesis_id, _roads_shadow_computation_details.request_date_time
    )
    stats_key = get_synthesis_roads_shadow_stats_key(
        synthesis_id, _roads_shadow_computation_details.request_date_time
    )

    # The design is final: if a non-empty analysis was already computed for this
    # design there is nothing to do. A cached zero result is treated as invalid
    # (it normally means the roads download failed) and is recomputed.
    if r.exists(stats_key):
        try:
            existing_stats = json.loads(r.get(stats_key).decode("utf-8"))
        except (AttributeError, TypeError, ValueError):
            existing_stats = {}
        if not isinstance(existing_stats, dict):
            existing_stats = {}
        if existing_stats.get("total_roads_kms", 0) > 0:
            logger.info(
                "Road/shadow stats already cached for %s; skipping recomputation",
                stats_key,
            )
            return
        logger.info(
            "Cached road/shadow stats for %s are empty; recomputing", stats_key
        )

    shadows_str = r.get(shadows_key)
    if shadows_str is None:
        logger.error("Shadows not found in redis for key %s", shadows_key)
        if r.exists(stats_key):
            # Do not leave a misleading zero result cached.
            r.delete(stats_key)
        return
    shadows = json.loads(shadows_str.decode("utf-8"))
    bounds = _roads_shadow_computation_details.bounds
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    roads_storage_key = bounds_hash[:15] + ":roads"
    roads_str = r.get(roads_storage_key)
    if roads_str is None:
        logger.error("Roads not found in redis for key %s", roads_storage_key)
        if r.exists(stats_key):
            r.delete(stats_key)
        return
    roads = json.loads(roads_str.decode("utf-8"))
    if not roads.get("features"):
        logger.error(
            "Bike routes for key %s are empty; skipping shadow/bike-route "
            "analysis. Check the FULL_ROAD_NETWORK_GEOSJON_* URL for this project.",
            roads_storage_key,
        )
        if r.exists(stats_key):
            # Do not leave a misleading zero result cached.
            r.delete(stats_key)
        return
    shadow_roads_intersection_data = ShadowsRoadsIntersectionRequest(
        roads=json.dumps(roads),
        shadows=shadows,
        job_id=stats_key,
    )

    compute_road_shadow_overlap(
        roads_shadows_data=asdict(shadow_roads_intersection_data)
    )
    # logger.info(shadow_roads_intersection_data)


def drawn_trees_compute_shadow(tree_processing_payload: dict):
    """This method computes the shadow of drawn trees"""

    _drawn_trees_shadow_request = from_dict(
        data_class=DrawnTreesShadowGenerationRequest,
        data=tree_processing_payload,
    )

    # buffer them
    my_drawn_trees_helper = DrawnTreesProcessor()
    _processed_trees = my_drawn_trees_helper.process_drawn_trees_data(
        unprocessed_tree_geojson=_drawn_trees_shadow_request.trees
    )

    _drawn_trees_shadow_request.processed_trees = _processed_trees
    _date_time = arrow.get(_drawn_trees_shadow_request.request_date_time).isoformat()

    processed_trees_serialzed = json.loads(geojson.dumps(_processed_trees))
    trees = gpd.GeoDataFrame.from_features(processed_trees_serialzed["features"])
    _shadow_date_time = get_default_shadow_datetime()
    _pd_date_time = pd.to_datetime(_shadow_date_time).tz_localize("UTC")
    shadows = pybdshadow.bdshadow_sunlight(trees, _pd_date_time)
    dissolved_shadows = shadows.dissolve()

    redis_key = (
        _drawn_trees_shadow_request.session_id
        + "_"
        + _drawn_trees_shadow_request.state_id
        + "_drawn_trees_shadow"
    )

    r.set(redis_key, json.dumps(dissolved_shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    logger.info("Job Completed...")


def _read_fgb_layer(layer_url: str, bounds: str, storage_suffix: str) -> dict:
    """Download a FlatGeobuf layer and cache it in redis keyed by bounds hash.

    Follows the same caching pattern as ``download_trees`` /
    ``download_existing_buildings``: a successful download is cached for a
    long time, a failed one briefly so a corrected URL recovers quickly.
    """

    empty_fc = {"type": "FeatureCollection", "features": []}
    if not layer_url:
        return empty_fc

    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    storage_key = f"{bounds_hash[:15]}:{storage_suffix}"

    if r.exists(storage_key):
        cached = json.loads(r.get(storage_key))
        if isinstance(cached, dict) and cached.get("features"):
            return cached

    bounds_filtering = _use_bounds_filtering()
    url = layer_url.replace("__bounds__", bounds) if bounds_filtering else layer_url

    fc = empty_fc
    try:
        download_request = requests.get(url, timeout=120)
        if download_request.status_code == 200:
            # pyogrio (geopandas) reads FlatGeobuf from a local file
            with tempfile.NamedTemporaryFile(suffix=".fgb", delete=False) as tmp:
                tmp.write(download_request.content)
                tmp_path = tmp.name
            try:
                gdf = gpd.read_file(tmp_path)
                fc = json.loads(gdf.to_json())
            finally:
                os.remove(tmp_path)
        else:
            logger.error(
                "Error downloading %s layer from %s (HTTP %s)",
                storage_suffix,
                layer_url,
                download_request.status_code,
            )
    except Exception as e:
        logger.error("Error reading %s layer from %s: %s", storage_suffix, layer_url, e)

    if fc.get("features"):
        r.set(storage_key, json.dumps(fc))
        r.expire(storage_key, time=60000)
    else:
        r.set(storage_key, json.dumps(empty_fc), ex=300)
    return fc


def _features_to_gdf(features: list):
    """Build a WGS84 GeoDataFrame from GeoJSON features, tolerating empty input.

    ``GeoDataFrame.from_features([])`` raises, so construct an explicit empty
    frame in that case.
    """
    if features:
        return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def compute_site_evaluation(site_evaluation_payload: dict):
    """Background job: compute 3/30/300 site evaluation layers for drawn trees.

    Produces two GeoJSON layers:
      - building_priority_zones: 50 m buffers around building centroids,
        classified by the number of drawn trees within 50 m (high = 0 trees,
        medium = 1-2, met = >= 3) and dissolved per priority class, so
        overlapping buffers of the same type merge into a single zone.
      - coverage_gap: study area minus a 300 m buffer around the *actual*
        green space polygons (Rule 300), i.e. areas further than 300 m
        from any green space.

    The result is stored in redis under
    ``{session_id}_{state_id}_site_evaluation``.
    """

    _site_evaluation_request = from_dict(
        data_class=SiteEvaluationGenerationRequest, data=site_evaluation_payload
    )

    session_id = _site_evaluation_request.session_id
    state_id = _site_evaluation_request.state_id
    bounds = _site_evaluation_request.bounds

    # ── Drawn trees (only Point features are trees) ────────────────────────
    trees = _site_evaluation_request.trees
    if isinstance(trees, dict):
        trees = trees.get("features", [])
    point_features = [
        f for f in (trees or []) if f.get("geometry", {}).get("type") == "Point"
    ]
    trees_gdf = _features_to_gdf(point_features)

    # ── Study area (project bounds bbox) ───────────────────────────────────
    minx, miny, maxx, maxy = [float(c) for c in bounds.split(",")]
    study_area = ShapelyBox(minx, miny, maxx, maxy)
    study_gdf = gpd.GeoDataFrame(geometry=[study_area], crs="EPSG:4326")
    utm_crs = study_gdf.estimate_utm_crs()
    study_area_utm = study_gdf.to_crs(utm_crs).geometry.iloc[0]

    # ── Analytical layers ──────────────────────────────────────────────────
    buildings_fc = _read_fgb_layer(
        _site_evaluation_request.buildings_url, bounds, "existing_buildings"
    )
    greenspaces_fc = _read_fgb_layer(
        _site_evaluation_request.greenspaces_url, bounds, "existing_greenspaces"
    )
    buildings_gdf = _features_to_gdf(buildings_fc["features"])
    if not buildings_gdf.empty:
        # FGB files are downloaded whole; only evaluate buildings in the study area
        buildings_gdf = buildings_gdf[buildings_gdf.intersects(study_area)]
    greenspaces_gdf = _features_to_gdf(greenspaces_fc["features"])

    empty_fc = {"type": "FeatureCollection", "features": []}
    priority_fc = empty_fc
    gap_fc = empty_fc
    stats = {}
    messages = []

    # ── Rule 3 — Building Priority Zones (dissolved per priority) ──────────
    if not buildings_gdf.empty:
        buildings_utm = buildings_gdf.to_crs(utm_crs)
        trees_utm = trees_gdf.to_crs(utm_crs)

        priority_buffers = {"high": [], "medium": [], "met": []}
        priority_building_counts = {"high": 0, "medium": 0, "met": 0}
        priority_tree_counts = {"high": 0, "medium": 0, "met": 0}

        for building_geom in buildings_utm.geometry:
            centroid = building_geom.centroid
            buffer_50m = centroid.buffer(50)
            if trees_utm.empty:
                tree_count = 0
            else:
                tree_count = int(trees_utm.geometry.within(buffer_50m).sum())
            if tree_count == 0:
                priority = "high"
            elif tree_count < 3:
                priority = "medium"
            else:
                priority = "met"
            priority_buffers[priority].append(buffer_50m)
            priority_building_counts[priority] += 1
            priority_tree_counts[priority] += tree_count

        # Dissolve buffers of the same priority class into a single zone
        dissolved_zones = []
        for priority in ("high", "medium", "met"):
            geoms = priority_buffers[priority]
            if not geoms:
                continue
            dissolved = unary_union(geoms)
            dissolved_zones.append(
                {
                    "geometry": dissolved,
                    "priority": priority,
                    "building_count": priority_building_counts[priority],
                    "tree_count": priority_tree_counts[priority],
                }
            )

        if dissolved_zones:
            zones_gdf = gpd.GeoDataFrame(
                dissolved_zones,
                geometry="geometry",
                crs=utm_crs,
            )
            priority_fc = json.loads(zones_gdf.to_crs("EPSG:4326").to_json())

        stats["high_buildings"] = priority_building_counts["high"]
        stats["medium_buildings"] = priority_building_counts["medium"]
        stats["met_buildings"] = priority_building_counts["met"]
        stats["total_buildings"] = int(len(buildings_utm))
        rule3_msg = (
            "3-tree rule: {met} of {total} buildings have ≥3 trees within 50 m".format(
                met=priority_building_counts["met"],
                total=int(len(buildings_utm)),
            )
        )
        if priority_building_counts["high"] > 0:
            rule3_msg += "; {high} have none".format(
                high=priority_building_counts["high"]
            )
        if priority_building_counts["medium"] > 0:
            rule3_msg += "; {medium} have 1–2 trees".format(
                medium=priority_building_counts["medium"]
            )
        messages.append(rule3_msg)
    else:
        messages.append("Buildings layer unavailable")

    # ── Rule 300 — Green Space Coverage Gap ────────────────────────────────
    # Buffer the actual green space polygons (not their centroids) by 300 m;
    # the gap is the part of the study area outside that buffered coverage.
    if _site_evaluation_request.greenspaces_url:
        if greenspaces_gdf.empty:
            gap_geom_utm = study_area_utm
        else:
            greenspaces_utm = greenspaces_gdf.to_crs(utm_crs)
            green_union = unary_union(greenspaces_utm.geometry.values)
            coverage_utm = green_union.buffer(300)
            gap_geom_utm = study_area_utm.difference(coverage_utm)

        study_area_sqm = study_area_utm.area
        gap_sqm = gap_geom_utm.area if not gap_geom_utm.is_empty else 0
        gap_percentage = (
            (gap_sqm / study_area_sqm) * 100 if study_area_sqm > 0 else 0
        )
        stats["gap_percentage"] = round(gap_percentage, 1)
        if not gap_geom_utm.is_empty and gap_geom_utm.area > 0:
            gap_gdf = gpd.GeoDataFrame(
                [{"geometry": gap_geom_utm}], geometry="geometry", crs=utm_crs
            )
            gap_fc = json.loads(gap_gdf.to_crs("EPSG:4326").to_json())
            messages.append(
                "{pct}% of study area is more than 300 m from a green space".format(
                    pct=stats["gap_percentage"]
                )
            )
    else:
        messages.append("Green Spaces layer unavailable")

    result = {
        "building_priority_zones": priority_fc,
        "coverage_gap": gap_fc,
        "stats": stats,
        "messages": messages,
    }

    redis_key = f"{session_id}_{state_id}_site_evaluation"
    r.set(redis_key, json.dumps(result))
    r.expire(redis_key, time=6000)
    logger.info("Site evaluation job with key %s completed", redis_key)


def compute_existing_buildings_shadow_with_tree_canopy(geojson_session_date_time: dict):
    _existing_building_date_time = from_dict(
        data_class=ExistingBuildingsDataShadowGenerationRequest,
        data=geojson_session_date_time,
    )
    _date_time = arrow.get(_existing_building_date_time.request_date_time).isoformat()
    _pd_date_time = pd.to_datetime(_date_time).tz_convert("UTC")
    # Combine trees and buildings into one FC

    bounds = _existing_building_date_time.bounds
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    trees_hash_key = bounds_hash[:15] + ":trees"
    existing_buildings_hash_key = bounds_hash[:15] + ":existing_buildings"

    _existing_buildings_raw = r.get(existing_buildings_hash_key)
    existing_buildings_fc = json.loads(_existing_buildings_raw)

    existing_buildings = gpd.GeoDataFrame.from_features(
        existing_buildings_fc["features"]
    )

    existing_buildings_shadows = pybdshadow.bdshadow_sunlight(
        existing_buildings, _pd_date_time
    )

    # Merge the canopy with the shadow
    downloaded_trees_raw = r.get(trees_hash_key)
    downloaded_tree_canopy_fc = json.loads(downloaded_trees_raw)
    _downloaded_tree_canopy_features = downloaded_tree_canopy_fc["features"]
    canopy_gdf = gpd.GeoDataFrame.from_features(_downloaded_tree_canopy_features)

    ## Merge the downloaded tree canopy with shadows
    combined_shadows = pd.concat([existing_buildings_shadows, canopy_gdf])

    dissolved_shadows = combined_shadows.dissolve()

    redis_key = (
        _existing_building_date_time.session_id
        + ":"
        + _existing_building_date_time.request_date_time
        + "_existing_buildings_canopy_shadow"
    )
    r.set(redis_key, dissolved_shadows.to_json())
    r.expire(redis_key, time=6000)
    time.sleep(7)
    logger.info("Existing Buildings + Canopy Shadow Completed")


def compute_gdh_shadow_with_tree_canopy(geojson_session_date_time: dict):
    _diagramid_building_date_time = from_dict(
        data_class=GeodesignhubDataShadowGenerationRequest,
        data=geojson_session_date_time,
    )

    synthesis_id = _get_synthesis_id(
        _diagramid_building_date_time, _diagramid_building_date_time.session_id
    )
    redis_key = get_synthesis_shadow_key(
        synthesis_id, _diagramid_building_date_time.request_date_time
    )

    # The design is final, so its shadow does not change. Reuse the cached
    # result instead of recomputing it every time the design is opened.
    if r.exists(redis_key):
        logger.info(
            "Design shadow already cached for %s; skipping recomputation", redis_key
        )
        return

    _date_time = arrow.get(_diagramid_building_date_time.request_date_time).isoformat()
    gdh_design_diagram_buildings = gpd.GeoDataFrame.from_features(
        _diagramid_building_date_time.buildings["features"]
    )
    exploded_gdh_buildings = gdh_design_diagram_buildings.explode()
    _exploded_gdh_building_polygons = exploded_gdh_buildings[
        exploded_gdh_buildings.geometry.type != "LineString"
    ]
    _pd_date_time = pd.to_datetime(_date_time).tz_convert("UTC")
    shadows = pybdshadow.bdshadow_sunlight(
        _exploded_gdh_building_polygons, _pd_date_time
    )

    # Remove building footprints from the computed shadows so that the final
    # shadow geometry only contains the shadow cast by the buildings and not
    # the buildings themselves. Trees (is_tree == 1) are kept so that the tree
    # cylinders remain part of the shadows.
    if "is_tree" in _exploded_gdh_building_polygons.columns:
        non_tree_buildings = _exploded_gdh_building_polygons[
            _exploded_gdh_building_polygons["is_tree"] != 1
        ]
    else:
        non_tree_buildings = _exploded_gdh_building_polygons

    building_footprints = non_tree_buildings.geometry.union_all()
    if not building_footprints.is_empty:
        shadows = shadows.copy()
        shadows["geometry"] = shadows.geometry.difference(building_footprints)
        shadows = shadows[~shadows.geometry.is_empty]

    # # Merge the canopy with the shadow
    # bounds = _diagramid_building_date_time.bounds
    # # Combine trees and buildings into one FC
    # bounds_hash= hashlib.sha512(bounds.encode('utf-8')).hexdigest()
    # bounds_hash_key = bounds_hash[:15] + ':trees'
    # downloaded_trees_raw = r.get(bounds_hash_key)

    # downloaded_tree_canopy_fc = json.loads(downloaded_trees_raw)
    # _downloaded_tree_canopy_features = downloaded_tree_canopy_fc['features']
    # canopy_gdf = gpd.GeoDataFrame.from_features(_downloaded_tree_canopy_features)

    # ## Merge the downloaded tree canopy with shadows
    # combined_shadows = pd.concat([shadows, canopy_gdf])

    dissolved_shadows = shadows.dissolve()

    r.set(redis_key, json.dumps(dissolved_shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    logger.info("Job Completed")


def compute_polygon_area(polygon: ShapelyPolygon):
    geod = Geod(ellps="WGS84")
    poly_area_m2, poly_perimeter = geod.geometry_area_perimeter(polygon)
    poly_area_hectares = poly_area_m2 / 10000  # convert from m^2 to hectares
    return poly_area_hectares


def compute_road_shadow_overlap(
    roads_shadows_data: ShadowsRoadsIntersectionRequest,
) -> None:
    _roads_shadows_data = from_dict(
        data_class=ShadowsRoadsIntersectionRequest, data=roads_shadows_data
    )
    roads_str = _roads_shadows_data.roads
    shadows_str = _roads_shadows_data.shadows

    job_id = _roads_shadows_data.job_id
    geod = Geod(ellps="WGS84")
    roads = json.loads(roads_str)
    shadows = json.loads(shadows_str)

    all_roads = [
        (
            ShapelyLineString(coordinates=feature["geometry"]["coordinates"])
            if feature["geometry"]["type"] == "LineString"
            else ShapelyMultiLineString(feature["geometry"]["coordinates"])
        )
        for feature in roads["features"]
    ]

    total_length = sum(geod.geometry_length(line) for line in all_roads)
    logger.info(f"Total Roads Length: {total_length:.3f}")

    gdh_sahdows_gpd = gpd.GeoDataFrame.from_features(shadows["features"])
    exploded_gdh_shadows = gdh_sahdows_gpd.explode()
    all_shadows = [
        ShapelyPolygon(shadow.geometry.exterior.coords)
        for shadow in exploded_gdh_shadows.itertuples()
        if shadow.geometry.geom_type == "Polygon"
    ]

    total_shadow_area = sum(compute_polygon_area(orient(s)) for s in all_shadows)
    logger.info(f"Total Shadow Area: {total_shadow_area:.3f}")

    roads_tree = STRtree(all_roads)
    shadowed_kms = sum(
        geod.geometry_length(all_roads[relevant_road].intersection(current_s))
        for current_s in all_shadows
        for relevant_road in roads_tree.query(current_s, predicate="intersects")
    )

    road_shadow_overlap = RoadsShadowOverlap(
        total_roads_kms=round(total_length, 2),
        shadowed_kms=round(shadowed_kms, 2),
        job_id=job_id,
        total_shadow_area=round(total_shadow_area, 2),
    )

    r.set(job_id, json.dumps(asdict(road_shadow_overlap)))
    # Keep the stats aligned with the shadow cache lifetime so they are
    # recomputed after the underlying shadow expires.
    r.expire(job_id, time=6000)
    time.sleep(1)
    logger.info("Intersection Completed")
