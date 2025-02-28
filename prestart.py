from sqlalchemy import text
from dashboard import create_app

if __name__ == "__main__":
    app, flask_babel, db = create_app()
    
    db.session.execute(text("SELECT 1"))

