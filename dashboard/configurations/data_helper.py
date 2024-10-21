from networkx import project
import yaml
from data_definitions import (
    COGLayer,
    WMSLayer,
    WMSLayerList,
    COGLayerList,
    LayersAvailableInAllViews,
)
from typing import Union, List
from dotenv import load_dotenv, find_dotenv
import logging
import os

logger = logging.getLogger("local-climate-response")

load_dotenv(find_dotenv())
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


class ViewDataGenerator:
    def __init__(self, view_type: str, project_id: str):
        self.project_id = project_id
        self.view_type = view_type
        self.all_external_data: LayersAvailableInAllViews = (
            self._parse_load_layers_to_display()
        )

    def _parse_load_layers_to_display(self) -> LayersAvailableInAllViews:

        with open("external_layers.yaml", "r") as stream:
            configurations_dict = yaml.safe_load(stream)
        # COGS layers
        all_cog_layers: List[COGLayer] = []
        for cog_layer in configurations_dict["cogs"]:
            environment_key = cog_layer["environment_key"]

            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                cog_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("PROJECT_ID", "")
                cog_url = os.getenv(generic_key, 0)

            if cog_url:
                cog_layer = COGLayer(
                    url=cog_url, name=cog_layer["name"], dom_id=cog_layer["dom_id"]
                )
        # WMS Layers
        all_wms_layers: List[WMSLayer] = []
        for wms_layer in configurations_dict["wms"]:
            environment_key = wms_layer["environment_key"]

            project_specific_url = environment_key.replace(
                "PROJECT_ID", self.project_id
            )

            if os.getenv(project_specific_url, None) is not None:
                wms_url = os.getenv(project_specific_url)
            else:
                generic_key = environment_key.replace("PROJECT_ID", "")
                wms_url = os.getenv(generic_key, 0)

            if cog_url:
                cog_layer = WMSLayer(
                    url=wms_url, name=wms_layer["name"], dom_id=wms_layer["dom_id"]
                )
        # TODO: COGS layers
        # TODO: PMTiles layers

        _layers_available_in_all_views = LayersAvailableInAllViews(
            cogs=all_cog_layers, wms=all_wms_layers
        )

        return _layers_available_in_all_views


    def generate_wms_layers_list(self) -> WMSLayerList:
        return self.all_external_data.wms

    def generate_cog_layers_list(self) -> COGLayerList:
        return self.all_external_data.cogs
