import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    serviceurl= os.environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/"),
    REDIS_URL= os.environ.get("REDIS_URL", 'redis://localhost:6379')
    ROADS_URL = os.environ.get("ROADS_URL", None)
    LANGUAGES = {
    'en': 'English',
    'he': 'Hebrew',
    'ar': 'Arabic'

  }

apisettings = {
  "serviceurl": os.environ.get("SERVICE_URL", "https://www.geodesignhub.com/api/v1/")
}
