import yaml
from data_definitions import (
    COGLayer,
    FGBDataSource,
    GeoJSONDataSource,
    GeoJSONDataSourceList,
    PMTilesDataSource,
    PMTilesDataSourceList,
    WMSLayer,
    WMSDataSourceList,
    COGDataSourceList,
    FGBDataSourceList,
    LayersAvailableInSpecificViews,
    GeoJSONDataSourceList,
    CommonDataForAllViews,
)
from typing import List, Union
from dotenv import load_dotenv, find_dotenv
import logging
import os
from config import BASE_DIR

logger = logging.getLogger("local-climate-response")

load_dotenv(find_dotenv())
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


class ViewDataGenerator:
    def __init__(self, view_type: Union[str, None], project_id: str):
        self.project_id = project_id
        self.view_type = view_type
        self.all_external_data: Union[list, LayersAvailableInSpecificViews] = (
            self._parse_load_layers_to_display() if view_type else []
        )

        self.common_data_for_project: CommonDataForAllViews = (
            self._parse_load_common_data_to_process()
        )

    def _load_blueprint(self):

        blueprint_filename = "external_layers.yaml"
        blueprint_path = os.path.join(
            BASE_DIR, "dashboard", "configurations", blueprint_filename
        )
        if not os.path.isfile(blueprint_path):
            raise Exception(
                "Invalid Blueprint: %s is incorrect, please provide one that exists"
                % blueprint_filename
            )

        with open(blueprint_path, "r") as stream:
            configurations_dict = yaml.safe_load(stream)

        return configurations_dict

    def _parse_load_common_data_to_process(self) -> CommonDataForAllViews:
        configurations_dict = self._load_blueprint()
        current_view_dictionary = configurations_dict["common"]
        all_geojson_layers: List[GeoJSONDataSource] = []

        for geojson_layer in current_view_dictionary["geojson"]:
            environment_key = geojson_layer["environment_key"]
            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                geojson_layer_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("_PROJECT_ID", "")
                geojson_layer_url = os.getenv(generic_key, 0)

            if geojson_layer_url:
                single_geojson_layer = GeoJSONDataSource(
                    url=geojson_layer_url, name=geojson_layer["name"]
                )
                all_geojson_layers.append(single_geojson_layer)

        _layers_available_in_all_views = CommonDataForAllViews(
            geojson_layers=all_geojson_layers,
        )

        return _layers_available_in_all_views

    def get_existing_roads_geojson_url(self) -> Union[None, GeoJSONDataSource]:
        all_common_geojson_sources = self.common_data_for_project.geojson_layers

        for all_common_geojson_source in all_common_geojson_sources:
            if all_common_geojson_source.name == "Existing Roads":
                return all_common_geojson_source

        return None

    def _parse_load_layers_to_display(self) -> LayersAvailableInSpecificViews:

        configurations_dict = self._load_blueprint()
        current_view_dictionary = configurations_dict[self.view_type]
        all_cog_layers: List[COGLayer] = []

        for cog_layer in current_view_dictionary["cogs"]:
            environment_key = cog_layer["environment_key"]

            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                cog_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("_PROJECT_ID", "")
                cog_url = os.getenv(generic_key, 0)

            if cog_url:
                single_cog_layer = COGLayer(
                    url=cog_url, name=cog_layer["name"], dom_id=cog_layer["dom_id"]
                )
                all_cog_layers.append(single_cog_layer)
        # WMS Layers
        all_wms_layers: List[WMSLayer] = []
        for wms_layer in current_view_dictionary["wms"]:
            environment_key = wms_layer["environment_key"]

            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                wms_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("_PROJECT_ID", "")
                wms_url = os.getenv(generic_key, 0)

            if wms_url:
                single_wms_layer = WMSLayer(
                    url=wms_url, name=wms_layer["name"], dom_id=wms_layer["dom_id"]
                )
                all_wms_layers.append(single_wms_layer)

        all_fgb_layers: List[FGBDataSource] = []

        for fgb_layer in current_view_dictionary["fgb"]:
            environment_key = fgb_layer["environment_key"]
            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                fgb_layer_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("_PROJECT_ID", "")
                fgb_layer_url = os.getenv(generic_key, 0)

            if fgb_layer_url:
                single_fgb_layer = FGBDataSource(
                    url=fgb_layer_url,
                    name=fgb_layer["name"],
                    dom_id=fgb_layer["dom_id"],
                    color=fgb_layer["color"],
                    geometry_type=fgb_layer["geometry_type"],
                )
                all_fgb_layers.append(single_fgb_layer)

        all_pmtiles_layers: List[PMTilesDataSource] = []
        for pmtiles_layer in current_view_dictionary["pmtiles"]:
            environment_key = pmtiles_layer["environment_key"]

            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                pmtiles_layer_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("_PROJECT_ID", "")
                pmtiles_layer_url = os.getenv(generic_key, 0)

            if pmtiles_layer_url:
                single_pmtiles_layer = PMTilesDataSource(
                    url=pmtiles_layer_url,
                    name=pmtiles_layer["name"],
                    dom_id=pmtiles_layer["dom_id"],
                    layer_type=pmtiles_layer["layer_type"],
                )
                all_pmtiles_layers.append(single_pmtiles_layer)

        _layers_available_in_specific_views = LayersAvailableInSpecificViews(
            cogs=all_cog_layers,
            wms=all_wms_layers,
            pmtiles=all_pmtiles_layers,
            fgb_layers=all_fgb_layers,
        )

        return _layers_available_in_specific_views

    def generate_wms_layers_list(self) -> WMSDataSourceList:
        return WMSDataSourceList(layers=self.all_external_data.wms)

    def generate_cog_layers_list(self) -> COGDataSourceList:
        return COGDataSourceList(layers=self.all_external_data.cogs)

    def generate_pmtiles_layers_list(self) -> PMTilesDataSourceList:
        return PMTilesDataSourceList(layers=self.all_external_data.pmtiles)

    def generate_fgb_layers_list(self) -> FGBDataSourceList:
        return FGBDataSourceList(layers=self.all_external_data.fgb_layers)
