from flask import Flask
from config import Config
import os
from flask_babel import Babel
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def create_app(config_class=Config):   
    app = Flask(__name__) 
    app.config.from_object(config_class)
    babel = Babel(app)
    return app, babel