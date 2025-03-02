from flask import Flask
from config import Config
import os
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from dotenv import load_dotenv
from flask_migrate import Migrate, migrate
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass


def create_app(config_class=Config):   
    app = Flask(__name__) 
    app.config.from_object(config_class)
    babel = Babel(app)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy(model_class=Base)
    db.init_app(app)
    migrate = Migrate(app, db)


    return app, babel