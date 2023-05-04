from flask import Flask
from config import Config
from flask_sse import sse
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def create_app(config_class=Config):   
    app = Flask(__name__) 
    app.config.from_object(config_class)
    app.register_blueprint(sse, url_prefix='/stream')
    
    return app