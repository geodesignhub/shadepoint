from dotenv import load_dotenv
from os import environ
import os
from data_definitions import WMSLayer

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config(object):
    serviceurl = (
        os.environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/"),
    )
    REDIS_URL = environ.get("REDIS_URL", "redis://localhost:6379")
    LANGUAGES = {"en": "English", "he": "עִברִית", "ar": "عربي"}


apisettings = {
    "serviceurl": environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/")
}


class wms_url_generator:
    def __init__(self, project_id):
        self.project_id = project_id

    def get_ortho_photo_cog_url(self):

        project_specific_url = "ORTHO_PHOTO_{project_id}_COG_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            ortho_photo_url = environ.get(project_specific_url)
        else:
            ortho_photo_url = environ.get("ORTHO_PHOTO_COG_URL", "0")

        return ortho_photo_url

    def get_trees_wms_url(self):
        project_specific_url = "WMS_{project_id}_EXISTING_TREES_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            trees_wms_url = environ.get(project_specific_url)
        else:
            trees_wms_url = environ.get("WMS_EXISTING_TREES_URL", "0")

        return trees_wms_url

    def get_satellite_wms_url(self):
        project_specific_url = "WMS_{project_id}_SATELLITE_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            trees_wms_url = environ.get(project_specific_url)
        else:
            trees_wms_url = environ.get("WMS_SATELLITE_URL", "0")

        return trees_wms_url

    def get_baseline_index_wms_url(self):
        project_specific_baseline_index_url = (
            "WMS_{project_id}_BASELINE_SHADOW_INDEX".format(project_id=self.project_id)
        )
        if environ.get(project_specific_baseline_index_url, None) is not None:
            baseline_index_url = environ.get(project_specific_baseline_index_url)
        else:
            baseline_index_url = environ.get("WMS_BASELINE_SHADOW_INDEX", "0")

        return baseline_index_url

    def get_baseline_flood_vulnerability_url(self):
        project_specific_flood_vulnerability_wms_url = (
            "WMS_{project_id}_BASELINE_FLOOD_VULNERABILITY".format(
                project_id=self.project_id
            )
        )
        if environ.get(project_specific_flood_vulnerability_wms_url, None) is not None:
            flood_vulnerability_url = environ.get(
                project_specific_flood_vulnerability_wms_url
            )
        else:
            flood_vulnerability_url = environ.get("WMS_BASELINE_SHADOW_INDEX", "0")

        return flood_vulnerability_url

    def get_current_bike_network_wms(self) -> WMSLayer:
        project_specific_url = "WMS_{project_id}_CURRENT_BIKE_NETWORK_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            current_bike_network_url = environ.get(project_specific_url)
        else:
            current_bike_network_url = environ.get("WMS_CURRENT_BIKE_NETWORK_URL", "0")
        current_bike_network = WMSLayer(
            url=current_bike_network_url,
            name="Current Bike Network",
            dom_id="current_bike_network",
        )

        return current_bike_network

    def get_proposed_bike_network_wms(self) -> WMSLayer:
        project_specific_url = "WMS_{project_id}_PROPOSED_BIKE_NETWORK_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            proposed_bike_network_url = environ.get(project_specific_url)
        else:
            proposed_bike_network_url = environ.get(
                "WMS_PROPOSED_BIKE_NETWORK_URL", "0"
            )
        proposed_bike_network = WMSLayer(
            url=proposed_bike_network_url,
            name="Proposed Bike Network",
            dom_id="proposed_bike_network",
        )

        return proposed_bike_network

    def get_existing_bus_stops_wms(self) -> WMSLayer:
        project_specific_url = "WMS_{project_id}_BUS_STOPS_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            bus_stops_url = environ.get(project_specific_url)
        else:
            bus_stops_url = environ.get("WMS_BUS_STOPS_URL", "0")
        current_bike_network = WMSLayer(
            url=bus_stops_url,
            name="Bus Stops",
            dom_id="bus_stops",
        )

        return current_bike_network

    def get_roads_url(self):
        """
        This is the raw / GeoJSON url for roads
        """
        project_specific_url = "{project_id}_ROADS_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            trees_wms_url = environ.get(project_specific_url)
        else:
            trees_wms_url = environ.get("ROADS_URL", "0")

        return trees_wms_url

    def get_project_landuse_wms(self):
        """
        This is the raw / GeoJSON url for roads
        """
        project_specific_url = "{project_id}_LANDUSE_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            landuse_wms_url = environ.get(project_specific_url)
        else:
            landuse_wms_url = environ.get("LANDUSE_URL", "0")

        landuse_wms = WMSLayer(
            url=landuse_wms_url,
            name="Landuse",
            dom_id="current_landuse",
        )

        return landuse_wms

    def get_administrative_boundaries(self) -> WMSLayer:
        project_specific_url = "WMS_{project_id}_ADMINISTRATIVE_BOUNDARIES_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            bus_stops_url = environ.get(project_specific_url)
        else:
            bus_stops_url = environ.get("WMS_ADMINISTRATIVE_BOUNDARIES_URL", "0")
        current_bike_network = WMSLayer(
            url=bus_stops_url,
            name="Statistical Areas",
            dom_id="statistical_areas",
        )

        return current_bike_network

    def get_conservation_buildings(self) -> WMSLayer:
        project_specific_url = "WMS_{project_id}_CONSERVATION_BOUNDARIES_URL".format(
            project_id=self.project_id
        )
        if environ.get(project_specific_url, None) is not None:
            bus_stops_url = environ.get(project_specific_url)
        else:
            bus_stops_url = environ.get("WMS_CONSERVATION_BOUNDARIES_URL", "0")
        current_bike_network = WMSLayer(
            url=bus_stops_url,
            name="Conservation Buildings",
            dom_id="conservation_buildings",
        )

        return current_bike_network
