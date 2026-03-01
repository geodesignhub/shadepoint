from flask import Flask
from config import Config
import os
from flask_bootstrap import Bootstrap5
from flask_babel import Babel
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

from .extension import db, migrate

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    babel = Babel(app)
    Bootstrap5(app)
    CSRFProtect(app)
    db.init_app(app)
    migrate.init_app(app, db)

    from .nbsapi import nbsapi_blueprint
    app.register_blueprint(nbsapi_blueprint)

    return app, babel
