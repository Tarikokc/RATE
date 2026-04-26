# import sys
# sys.stdout.reconfigure(encoding='utf-8')

# import os
# from flask import Flask, send_from_directory
# from flask_cors import CORS
# from app.database import init_db, close_db
# from app.config import Config
# from app.routes.measures     import bp as measures_bp
# from app.routes.rooms        import bp as rooms_bp
# from app.routes.sensors      import bp as sensors_bp
# from app.routes.reservations import bp as reservations_bp
# from app.routes.heating      import bp as heating_bp
# from app.routes.predict      import bp as predict_bp

# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
# app.config.from_object(Config)

# app.register_blueprint(measures_bp)
# app.register_blueprint(rooms_bp)
# app.register_blueprint(sensors_bp)
# app.register_blueprint(reservations_bp)
# app.register_blueprint(heating_bp)
# app.register_blueprint(predict_bp)

# with app.app_context():
#     init_db()

# DIST = os.path.join(os.path.dirname(__file__), "clientApp", "dist", "client-app", "browser")

# @app.route("/", defaults={"path": ""})
# @app.route("/<path:path>")
# def serve_angular(path):
#     full = os.path.join(DIST, path)
#     if path and os.path.exists(full):
#         return send_from_directory(DIST, path)
#     return send_from_directory(DIST, "index.html")

# if __name__ == "__main__":
#     app.run(
#         host=Config.FLASK_HOST,
#         port=Config.FLASK_PORT,
#         debug=(Config.FLASK_ENV == "dev")
#     )
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.database import init_db, close_db
from app.config import Config
from app.routes.measures import bp as measures_bp
from app.routes.rooms import bp as rooms_bp
from app.routes.sensors import bp as sensors_bp
from app.routes.reservations import bp as reservations_bp
from app.routes.heating import bp as heating_bp
from app.routes.predict import bp as predict_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.teardown_appcontext(close_db)

app.register_blueprint(measures_bp)
app.register_blueprint(rooms_bp)
app.register_blueprint(sensors_bp)
app.register_blueprint(reservations_bp)
app.register_blueprint(heating_bp)
app.register_blueprint(predict_bp)

with app.app_context():
    init_db()

DIST = os.path.join(os.path.dirname(__file__), "clientApp", "dist", "client-app", "browser")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_angular(path):
    full = os.path.join(DIST, path)
    if path and os.path.exists(full):
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")

if __name__ == "__main__":
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=(Config.FLASK_ENV == "dev")
    )