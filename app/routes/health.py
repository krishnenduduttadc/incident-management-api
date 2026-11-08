from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():

    try:
        db.session.execute(text("SELECT 1"))

        return jsonify({
            "status": "UP",
            "application": "incident-management-api",
            "database": "CONNECTED"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "DOWN",
            "application": "incident-management-api",
            "database": "DISCONNECTED"
        }), 503
