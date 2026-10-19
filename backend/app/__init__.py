import os

from flask import Flask, jsonify

from .models import db


def create_app(config=None):
    app = Flask(__name__)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", ""),
        SECRET_KEY=os.environ.get("SECRET_KEY", ""),
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        TOKEN_MAX_AGE=int(os.environ.get("TOKEN_MAX_AGE", 60 * 60 * 12)),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    )
    if config:
        app.config.update(config)

    for key in ("SQLALCHEMY_DATABASE_URI", "SECRET_KEY", "ADMIN_PASSWORD"):
        if not app.config[key]:
            raise RuntimeError(f"{key} is not set. Check your environment variables.")

    db.init_app(app)

    from .routes import api

    app.register_blueprint(api, url_prefix="/api")

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify(error="Method not allowed"), 405

    return app
