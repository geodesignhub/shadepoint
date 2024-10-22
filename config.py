from dotenv import load_dotenv
from os import environ
import os
from data_definitions import WMSLayer
from pathlib import Path
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

BASE_DIR = Path(__file__).resolve().parent
class Config(object):
    serviceurl = (
        os.environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/"),
    )
    REDIS_URL = environ.get("REDIS_URL", "redis://localhost:6379")
    LANGUAGES = {"en": "English", "he": "עִברִית", "ar": "عربي"}


apisettings = {
    "serviceurl": environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/")
}

