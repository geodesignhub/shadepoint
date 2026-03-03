import logging
import sys

from sqlalchemy import text
from flask_migrate import upgrade

from dashboard import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations(app):
    with app.app_context():
        logger.info("Running database migrations...")
        upgrade()
        logger.info("Migrations complete.")


def check_db(app):
    with app.app_context():
        from dashboard.extension import db

        db.session.execute(text("SELECT 1"))
        db.session.remove()
        logger.info("Database connection verified.")


if __name__ == "__main__":
    app, _ = create_app()

    try:
        run_migrations(app)
        check_db(app)
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

    logger.info("Pre-start checks passed.")