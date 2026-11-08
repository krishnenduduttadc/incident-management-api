
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True)
    userid = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    cr_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )


class Vendor(db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.BigInteger, primary_key=True)
    vendorid = db.Column(db.String(100), unique=True)
    vendordesc = db.Column(db.String(500), nullable=False)
    cr_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )


class IncidentType(db.Model):
    __tablename__ = "incident_type"

    id = db.Column(db.BigInteger, primary_key=True)
    type_code = db.Column(db.String(50), unique=True, nullable=False)
    incidentdesc = db.Column(db.String(255))
    cr_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )


class IncidentStatus(db.Model):
    __tablename__ = "incident_status"

    id = db.Column(db.BigInteger, primary_key=True)
    status_code = db.Column(db.String(50), unique=True, nullable=False)
    status_desc = db.Column(db.String(255))
    cr_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )


class Incident(db.Model):
    __tablename__ = "incident"

    id = db.Column(db.BigInteger, primary_key=True)

    incidentsubject = db.Column(db.String(255), nullable=False)
    incidentdesc = db.Column(db.Text)

    created_by = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )

    incident_type_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident_type.id")
    )

    priority = db.Column(db.String(20), default="MEDIUM")

    cr_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )

    updated_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )


class IncidentMapping(db.Model):
    __tablename__ = "incident_mapping"

    id = db.Column(db.BigInteger, primary_key=True)

    incident_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident.id"),
        nullable=False,
        unique=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )

    vendor_id = db.Column(
        db.BigInteger,
        db.ForeignKey("vendors.id")
    )

    incident_status_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident_status.id"),
        nullable=False
    )

    assigned_by = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )

    assigned_at = db.Column(db.DateTime(timezone=True))

    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )


class IncidentHistory(db.Model):
    __tablename__ = "incident_history"

    id = db.Column(db.BigInteger, primary_key=True)

    incident_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident.id"),
        nullable=False
    )

    mapping_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident_mapping.id")
    )

    action = db.Column(db.String(50), nullable=False)

    old_status_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident_status.id")
    )

    new_status_id = db.Column(
        db.BigInteger,
        db.ForeignKey("incident_status.id")
    )

    old_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )

    new_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )

    old_vendor_id = db.Column(
        db.BigInteger,
        db.ForeignKey("vendors.id")
    )

    new_vendor_id = db.Column(
        db.BigInteger,
        db.ForeignKey("vendors.id")
    )

    changed_by_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )

    changed_by_vendor_id = db.Column(
        db.BigInteger,
        db.ForeignKey("vendors.id")
    )

    comments = db.Column(db.Text)

    cr_dt = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now()
    )
