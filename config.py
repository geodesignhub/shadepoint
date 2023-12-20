from dotenv import load_dotenv
from os import environ
import os 
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config(object):
    serviceurl = (
        os.environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/"),
    )
    REDIS_URL = environ.get("REDIS_URL", "redis://localhost:6379")
    ROADS_URL = environ.get("ROADS_URL", None)
    LANGUAGES = {"en": "English", "he": "עִברִית", "ar": "عربي"}


apisettings = {
    "serviceurl": environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/")
}

class wms_url_generator():
    def __init__(self, project_id):
        self.project_id = project_id

    def get_trees_wms_url(self):
        project_specific_url = "WMS_{project_id}_EXISTING_TREES_URL".format(project_id = self.project_id)
        if environ.get(project_specific_url) is not None:
            trees_wms_url = environ.get(project_specific_url)            
        else:
            trees_wms_url = environ.get("WMS_EXISTING_TREES_URL", "0")
        
        return trees_wms_url

    
    def get_baseline_index_wms_url(self):
        project_specific_baseline_index_url = "WMS_{project_id}_BASELINE_SHADOW_INDEX".format(project_id = self.project_id)
        if environ.get(project_specific_baseline_index_url) is not None:
            baseline_index_url = environ.get(project_specific_baseline_index_url)
        else:
            baseline_index_url = environ.get("WMS_BASELINE_SHADOW_INDEX", "0")
        
        return baseline_index_url


    def get_baseline_flood_vulnerability(self):
        projct_specific_flood_vulnerability_wms_url = "WMS_{project_id}_BASELINE_FLOOD_VULNERABILITY".format(project_id = self.project_id)
        if environ.get(projct_specific_flood_vulnerability_wms_url) is not None:
            flood_vulnerability_url = environ.get(projct_specific_flood_vulnerability_wms_url)
        else:
            flood_vulnerability_url = environ.get("WMS_BASELINE_SHADOW_INDEX", "0")
        
        return flood_vulnerability_url


    def get_roads_url(self):
        """ 
        This is the raw / GeoJSON url for roads
        """ 
        project_specific_url = "{project_id}_ROADS_URL".format(project_id = self.project_id)
        if environ.get(project_specific_url) is not None:
            trees_wms_url = environ.get(project_specific_url)            
        else:
            trees_wms_url = environ.get("ROADS_URL", "0")
        
        return trees_wms_url

    