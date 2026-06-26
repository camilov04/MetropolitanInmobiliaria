
from dotenv import load_dotenv
load_dotenv()

from app import app
from app.models import db

if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # crea todas las tablas
    app.run(debug=app.config.get("DEBUG", False))