
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, Vendor, IncidentType, IncidentStatus


resources_bp = Blueprint("resources", __name__)


def serialize(obj):
    result = {}

    for column in obj.__table__.columns:
        value = getattr(obj, column.name)

        if hasattr(value, "isoformat"):
            value = value.isoformat()

        result[column.name] = value

    return result


def register_crud(model, resource, allowed_fields, required_fields):

    collection = f"/{resource}"
    detail = f"/{resource}/<int:record_id>"

    def get_all():
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(
            max(request.args.get("per_page", 20, type=int), 1),
            100
        )

        pagination = (
            model.query
            .order_by(model.id)
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

        return jsonify({
            "data": [serialize(item) for item in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages
            }
        }), 200

    def create():
        data = request.get_json(silent=True) or {}

        missing = [
            field for field in required_fields
            if data.get(field) is None
        ]

        if missing:
            return jsonify({
                "error": "Missing required fields",
                "fields": missing
            }), 400

        obj = model(**{
            key: value
            for key, value in data.items()
            if key in allowed_fields
        })

        try:
            db.session.add(obj)
            db.session.commit()

            return jsonify(serialize(obj)), 201

        except IntegrityError:
            db.session.rollback()

            return jsonify({
                "error": "Duplicate value or invalid foreign key"
            }), 409

    def get_one(record_id):
        obj = db.session.get(model, record_id)

        if obj is None:
            return jsonify({"error": "Record not found"}), 404

        return jsonify(serialize(obj)), 200

    def update(record_id):
        obj = db.session.get(model, record_id)

        if obj is None:
            return jsonify({"error": "Record not found"}), 404

        data = request.get_json(silent=True) or {}

        for key, value in data.items():
            if key in allowed_fields:
                setattr(obj, key, value)

        try:
            db.session.commit()
            return jsonify(serialize(obj)), 200

        except IntegrityError:
            db.session.rollback()

            return jsonify({
                "error": "Duplicate value or invalid foreign key"
            }), 409

    def delete(record_id):
        obj = db.session.get(model, record_id)

        if obj is None:
            return jsonify({"error": "Record not found"}), 404

        try:
            db.session.delete(obj)
            db.session.commit()

            return "", 204

        except IntegrityError:
            db.session.rollback()

            return jsonify({
                "error": "Cannot delete this record because it is referenced by other records"
            }), 409

    resources_bp.add_url_rule(
        collection,
        endpoint=f"{resource}_list",
        view_func=get_all,
        methods=["GET"]
    )

    resources_bp.add_url_rule(
        collection,
        endpoint=f"{resource}_create",
        view_func=create,
        methods=["POST"]
    )

    resources_bp.add_url_rule(
        detail,
        endpoint=f"{resource}_get",
        view_func=get_one,
        methods=["GET"]
    )

    resources_bp.add_url_rule(
        detail,
        endpoint=f"{resource}_update",
        view_func=update,
        methods=["PUT"]
    )

    resources_bp.add_url_rule(
        detail,
        endpoint=f"{resource}_delete",
        view_func=delete,
        methods=["DELETE"]
    )


# USERS
register_crud(
    User,
    "users",
    ["userid", "username", "email", "active"],
    ["username"]
)

# VENDORS
register_crud(
    Vendor,
    "vendors",
    ["vendorid", "vendordesc"],
    ["vendordesc"]
)

# INCIDENT TYPES
register_crud(
    IncidentType,
    "incident-types",
    ["type_code", "incidentdesc"],
    ["type_code"]
)

# INCIDENT STATUSES
register_crud(
    IncidentStatus,
    "incident-statuses",
    ["status_code", "status_desc"],
    ["status_code"]
)
