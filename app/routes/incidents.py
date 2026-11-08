
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Incident,
    IncidentMapping,
    IncidentHistory,
    IncidentStatus,
    User,
    Vendor,
)
from app.routes.resources import serialize


incidents_bp = Blueprint("incidents", __name__)


PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def actor_from(data):
    user_id = data.get("changed_by_user_id")
    vendor_id = data.get("changed_by_vendor_id")

    if bool(user_id) == bool(vendor_id):
        return None

    if user_id and not db.session.get(User, user_id):
        return None

    if vendor_id and not db.session.get(Vendor, vendor_id):
        return None

    return {
        "changed_by_user_id": user_id,
        "changed_by_vendor_id": vendor_id
    }


def create_history(
    incident_id,
    mapping_id,
    action,
    actor,
    comments=None,
    old_status_id=None,
    new_status_id=None,
    old_user_id=None,
    new_user_id=None,
    old_vendor_id=None,
    new_vendor_id=None
):
    history = IncidentHistory(
        incident_id=incident_id,
        mapping_id=mapping_id,
        action=action,
        comments=comments,
        old_status_id=old_status_id,
        new_status_id=new_status_id,
        old_user_id=old_user_id,
        new_user_id=new_user_id,
        old_vendor_id=old_vendor_id,
        new_vendor_id=new_vendor_id,
        **actor
    )

    db.session.add(history)


# --------------------------------------------------
# INCIDENT CRUD
# --------------------------------------------------

@incidents_bp.route("/incidents", methods=["GET"])
def get_incidents():

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(
        max(request.args.get("per_page", 20, type=int), 1),
        100
    )

    query = Incident.query.order_by(Incident.id.desc())

    if request.args.get("priority"):
        query = query.filter_by(
            priority=request.args["priority"].upper()
        )

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    result = []

    for incident in pagination.items:
        item = serialize(incident)

        mapping = IncidentMapping.query.filter_by(
            incident_id=incident.id
        ).first()

        item["assignment"] = (
            serialize(mapping) if mapping else None
        )

        result.append(item)

    return jsonify({
        "data": result,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages
        }
    }), 200


@incidents_bp.route("/incidents/<int:incident_id>", methods=["GET"])
def get_incident(incident_id):

    incident = db.session.get(Incident, incident_id)

    if not incident:
        return jsonify({"error": "Incident not found"}), 404

    result = serialize(incident)

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).first()

    result["assignment"] = (
        serialize(mapping) if mapping else None
    )

    return jsonify(result), 200


@incidents_bp.route("/incidents", methods=["POST"])
def create_incident():

    data = request.get_json(silent=True) or {}

    required = [
        "incidentsubject",
        "created_by",
        "initial_status_id"
    ]

    missing = [
        field for field in required
        if data.get(field) is None
    ]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing
        }), 400

    priority = data.get("priority", "MEDIUM").upper()

    if priority not in PRIORITIES:
        return jsonify({
            "error": "Invalid priority",
            "allowed": sorted(PRIORITIES)
        }), 400

    creator = db.session.get(User, data["created_by"])
    status = db.session.get(
        IncidentStatus,
        data["initial_status_id"]
    )

    if not creator or not status:
        return jsonify({
            "error": "Invalid creator or initial status"
        }), 400

    try:
        incident = Incident(
            incidentsubject=data["incidentsubject"],
            incidentdesc=data.get("incidentdesc"),
            created_by=data["created_by"],
            incident_type_id=data.get("incident_type_id"),
            priority=priority
        )

        db.session.add(incident)
        db.session.flush()

        mapping = IncidentMapping(
            incident_id=incident.id,
            incident_status_id=status.id,
            updated_at=datetime.now(timezone.utc)
        )

        db.session.add(mapping)
        db.session.flush()

        create_history(
            incident_id=incident.id,
            mapping_id=mapping.id,
            action="CREATED",
            actor={
                "changed_by_user_id": creator.id,
                "changed_by_vendor_id": None
            },
            comments="Incident created",
            new_status_id=status.id
        )

        db.session.commit()

        return jsonify({
            "message": "Incident created successfully",
            "incident": serialize(incident),
            "assignment": serialize(mapping)
        }), 201

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "error": "Invalid incident data or foreign key reference"
        }), 409


@incidents_bp.route(
    "/incidents/<int:incident_id>",
    methods=["PUT"]
)
def update_incident(incident_id):

    incident = db.session.get(Incident, incident_id)

    if not incident:
        return jsonify({"error": "Incident not found"}), 404

    data = request.get_json(silent=True) or {}

    actor = actor_from(data)

    if not actor:
        return jsonify({
            "error": "Provide exactly one valid changed_by_user_id or changed_by_vendor_id"
        }), 400

    allowed = [
        "incidentsubject",
        "incidentdesc",
        "incident_type_id",
        "priority"
    ]

    if "priority" in data:
        data["priority"] = data["priority"].upper()

        if data["priority"] not in PRIORITIES:
            return jsonify({"error": "Invalid priority"}), 400

    old_subject = incident.incidentsubject

    for field in allowed:
        if field in data:
            setattr(incident, field, data[field])

    incident.updated_dt = datetime.now(timezone.utc)

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).first()

    try:
        create_history(
            incident_id=incident_id,
            mapping_id=mapping.id if mapping else None,
            action="UPDATED",
            actor=actor,
            comments=data.get(
                "comments",
                f"Incident updated. Previous subject: {old_subject}"
            )
        )

        db.session.commit()

        return jsonify(serialize(incident)), 200

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "error": "Invalid incident data"
        }), 409


@incidents_bp.route(
    "/incidents/<int:incident_id>",
    methods=["DELETE"]
)
def delete_incident(incident_id):

    incident = db.session.get(Incident, incident_id)

    if not incident:
        return jsonify({"error": "Incident not found"}), 404

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).first()

    history = IncidentHistory.query.filter_by(
        incident_id=incident_id
    ).first()

    if mapping or history:
        return jsonify({
            "error": "Physical deletion is not allowed for incidents with assignments or audit history",
            "recommendation": "Implement an archive/soft-delete operation"
        }), 409

    db.session.delete(incident)
    db.session.commit()

    return "", 204


# --------------------------------------------------
# INCIDENT ASSIGNMENT
# --------------------------------------------------

@incidents_bp.route(
    "/incidents/<int:incident_id>/assignment",
    methods=["GET"]
)
def get_assignment(incident_id):

    if not db.session.get(Incident, incident_id):
        return jsonify({"error": "Incident not found"}), 404

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).first()

    if not mapping:
        return jsonify({"error": "Assignment not found"}), 404

    return jsonify(serialize(mapping)), 200


@incidents_bp.route(
    "/incidents/<int:incident_id>/assignment",
    methods=["PUT"]
)
def assign_incident(incident_id):

    incident = db.session.get(Incident, incident_id)

    if not incident:
        return jsonify({"error": "Incident not found"}), 404

    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    vendor_id = data.get("vendor_id")
    assigned_by = data.get("assigned_by")

    # Exactly one assignee must be provided.
    if bool(user_id) == bool(vendor_id):
        return jsonify({
            "error": "Provide either user_id or vendor_id, not both"
        }), 400

    if not assigned_by or not db.session.get(User, assigned_by):
        return jsonify({"error": "Valid assigned_by user is required"}), 400

    if user_id and not db.session.get(User, user_id):
        return jsonify({"error": "User not found"}), 404

    if vendor_id and not db.session.get(Vendor, vendor_id):
        return jsonify({"error": "Vendor not found"}), 404

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).with_for_update().first()

    if not mapping:
        return jsonify({
            "error": "Incident mapping not found"
        }), 404

    old_user_id = mapping.user_id
    old_vendor_id = mapping.vendor_id

    action = (
        "ASSIGNED"
        if old_user_id is None and old_vendor_id is None
        else "REASSIGNED"
    )

    try:
        mapping.user_id = user_id
        mapping.vendor_id = vendor_id
        mapping.assigned_by = assigned_by

        now = datetime.now(timezone.utc)

        mapping.assigned_at = now
        mapping.updated_at = now

        create_history(
            incident_id=incident_id,
            mapping_id=mapping.id,
            action=action,
            actor={
                "changed_by_user_id": assigned_by,
                "changed_by_vendor_id": None
            },
            old_status_id=mapping.incident_status_id,
            new_status_id=mapping.incident_status_id,
            old_user_id=old_user_id,
            new_user_id=user_id,
            old_vendor_id=old_vendor_id,
            new_vendor_id=vendor_id,
            comments=data.get("comments")
        )

        db.session.commit()

        return jsonify({
            "message": "Incident assignment updated",
            "assignment": serialize(mapping)
        }), 200

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "error": "Assignment failed"
        }), 409


@incidents_bp.route(
    "/incidents/<int:incident_id>/assignment",
    methods=["DELETE"]
)
def unassign_incident(incident_id):

    data = request.get_json(silent=True) or {}

    actor = actor_from(data)

    if not actor:
        return jsonify({
            "error": "A valid acting user or vendor is required"
        }), 400

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).with_for_update().first()

    if not mapping:
        return jsonify({"error": "Assignment not found"}), 404

    old_user_id = mapping.user_id
    old_vendor_id = mapping.vendor_id

    if old_user_id is None and old_vendor_id is None:
        return jsonify({"error": "Incident is already unassigned"}), 409

    mapping.user_id = None
    mapping.vendor_id = None
    mapping.assigned_by = None
    mapping.assigned_at = None
    mapping.updated_at = datetime.now(timezone.utc)

    create_history(
        incident_id=incident_id,
        mapping_id=mapping.id,
        action="UNASSIGNED",
        actor=actor,
        old_status_id=mapping.incident_status_id,
        new_status_id=mapping.incident_status_id,
        old_user_id=old_user_id,
        old_vendor_id=old_vendor_id,
        comments=data.get("comments")
    )

    db.session.commit()

    return jsonify({
        "message": "Incident unassigned"
    }), 200


# --------------------------------------------------
# INCIDENT STATUS
# --------------------------------------------------

@incidents_bp.route(
    "/incidents/<int:incident_id>/status",
    methods=["PATCH"]
)
def change_status(incident_id):

    data = request.get_json(silent=True) or {}

    actor = actor_from(data)

    if not actor:
        return jsonify({
            "error": "A valid acting user or vendor is required"
        }), 400

    status_code = data.get("status_code")

    if not status_code:
        return jsonify({
            "error": "status_code is required"
        }), 400

    status = IncidentStatus.query.filter_by(
        status_code=status_code.upper()
    ).first()

    if not status:
        return jsonify({
            "error": "Unknown incident status"
        }), 404

    mapping = IncidentMapping.query.filter_by(
        incident_id=incident_id
    ).with_for_update().first()

    if not mapping:
        return jsonify({
            "error": "Incident mapping not found"
        }), 404

    old_status_id = mapping.incident_status_id

    if old_status_id == status.id:
        return jsonify({
            "error": "Incident already has this status"
        }), 409

    mapping.incident_status_id = status.id
    mapping.updated_at = datetime.now(timezone.utc)

    create_history(
        incident_id=incident_id,
        mapping_id=mapping.id,
        action="STATUS_CHANGED",
        actor=actor,
        old_status_id=old_status_id,
        new_status_id=status.id,
        old_user_id=mapping.user_id,
        new_user_id=mapping.user_id,
        old_vendor_id=mapping.vendor_id,
        new_vendor_id=mapping.vendor_id,
        comments=data.get("comments")
    )

    db.session.commit()

    return jsonify({
        "message": "Incident status updated",
        "status": serialize(status),
        "assignment": serialize(mapping)
    }), 200


# --------------------------------------------------
# INCIDENT MAPPING READ APIs
# Creation and modification happen through
# assignment/status operations above.
# --------------------------------------------------

@incidents_bp.route("/incident-mappings", methods=["GET"])
def get_mappings():

    mappings = IncidentMapping.query.order_by(
        IncidentMapping.id.desc()
    ).limit(100).all()

    return jsonify([
        serialize(mapping) for mapping in mappings
    ]), 200


@incidents_bp.route(
    "/incident-mappings/<int:mapping_id>",
    methods=["GET"]
)
def get_mapping(mapping_id):

    mapping = db.session.get(IncidentMapping, mapping_id)

    if not mapping:
        return jsonify({"error": "Mapping not found"}), 404

    return jsonify(serialize(mapping)), 200


# --------------------------------------------------
# INCIDENT HISTORY READ APIs
# --------------------------------------------------

@incidents_bp.route(
    "/incidents/<int:incident_id>/history",
    methods=["GET"]
)
def get_incident_history(incident_id):

    if not db.session.get(Incident, incident_id):
        return jsonify({"error": "Incident not found"}), 404

    page = max(request.args.get("page", 1, type=int), 1)

    per_page = min(
        max(request.args.get("per_page", 20, type=int), 1),
        100
    )

    query = IncidentHistory.query.filter_by(
        incident_id=incident_id
    )

    if request.args.get("action"):
        query = query.filter_by(
            action=request.args["action"].upper()
        )

    pagination = query.order_by(
        IncidentHistory.cr_dt.desc(),
        IncidentHistory.id.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return jsonify({
        "data": [
            serialize(item) for item in pagination.items
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages
        }
    }), 200


@incidents_bp.route(
    "/incident-history/<int:history_id>",
    methods=["GET"]
)
def get_history_record(history_id):

    history = db.session.get(
        IncidentHistory,
        history_id
    )

    if not history:
        return jsonify({"error": "History not found"}), 404

    return jsonify(serialize(history)), 200
