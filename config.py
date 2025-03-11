


from dotenv import load_dotenv
from os import environ
import os

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
    # Database configuration
    DB_ENGINE = os.getenv("DB_ENGINE")
    DB_USERNAME = os.getenv("DB_USERNAME")
    DB_HOSTNAME = os.getenv("DB_HOSTNAME")
    DB_NAME = os.getenv("DB_NAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_PORT = os.getenv("DB_PORT")

    # SQLAlchemy database URI
    SQLALCHEMY_DATABASE_URI = (
        f"{DB_ENGINE}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOSTNAME}:{DB_PORT}/{DB_NAME}"
    )



apisettings = {
    "serviceurl": environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/")
}
