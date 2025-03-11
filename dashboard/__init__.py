from flask import Flask
from config import Config
import os
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from dotenv import load_dotenv
from .extension import db, migrate
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
from sqlalchemy.orm import DeclarativeBase


def create_app(config_class=Config):   
    app = Flask(__name__) 
    app.config.from_object(config_class)
    babel = Babel(app)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)


    return app, babel