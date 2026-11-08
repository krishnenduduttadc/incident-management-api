
-- ============================================
-- 1. USERS
-- ============================================

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    userid VARCHAR(100) UNIQUE,
    username VARCHAR(150) NOT NULL,
    email VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    cr_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- 2. VENDORS
-- ============================================

CREATE TABLE vendors (
    id BIGSERIAL PRIMARY KEY,
    vendorid VARCHAR(100) UNIQUE,
    vendordesc VARCHAR(500) NOT NULL,
    cr_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- 3. INCIDENT TYPE
-- ============================================

CREATE TABLE incident_type (
    id BIGSERIAL PRIMARY KEY,
    type_code VARCHAR(50) UNIQUE NOT NULL,
    incidentdesc VARCHAR(255),
    cr_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- 4. INCIDENT STATUS
-- ============================================

CREATE TABLE incident_status (
    id BIGSERIAL PRIMARY KEY,
    status_code VARCHAR(50) UNIQUE NOT NULL,
    status_desc VARCHAR(255),
    cr_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- 5. INCIDENT
-- ============================================

CREATE TABLE incident (
    id BIGSERIAL PRIMARY KEY,
    incidentsubject VARCHAR(255) NOT NULL,
    incidentdesc TEXT,
    created_by BIGINT REFERENCES users(id),
    incident_type_id BIGINT REFERENCES incident_type(id),
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    cr_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- 6. INCIDENT MAPPING
-- Current assignment and status
-- ============================================

CREATE TABLE incident_mapping (
    id BIGSERIAL PRIMARY KEY,

    incident_id BIGINT NOT NULL UNIQUE
        REFERENCES incident(id),

    user_id BIGINT REFERENCES users(id),

    vendor_id BIGINT REFERENCES vendors(id),

    incident_status_id BIGINT NOT NULL
        REFERENCES incident_status(id),

    assigned_by BIGINT REFERENCES users(id),

    assigned_at TIMESTAMPTZ,

    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- 7. INCIDENT HISTORY
-- Immutable audit history
-- ============================================

CREATE TABLE incident_history (
    id BIGSERIAL PRIMARY KEY,

    incident_id BIGINT NOT NULL
        REFERENCES incident(id),

    mapping_id BIGINT
        REFERENCES incident_mapping(id),

    action VARCHAR(50) NOT NULL,

    old_status_id BIGINT
        REFERENCES incident_status(id),

    new_status_id BIGINT
        REFERENCES incident_status(id),

    old_user_id BIGINT
        REFERENCES users(id),

    new_user_id BIGINT
        REFERENCES users(id),

    old_vendor_id BIGINT
        REFERENCES vendors(id),

    new_vendor_id BIGINT
        REFERENCES vendors(id),

    changed_by_user_id BIGINT
        REFERENCES users(id),

    changed_by_vendor_id BIGINT
        REFERENCES vendors(id),

    comments TEXT,

    cr_dt TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- At least one actor must be recorded
    CHECK (
        changed_by_user_id IS NOT NULL
        OR changed_by_vendor_id IS NOT NULL
    ),

    -- An event cannot have two different actor types
    CHECK (
        changed_by_user_id IS NULL
        OR changed_by_vendor_id IS NULL
    )
);


-- ============================================
-- 8. INDEXES
-- ============================================

CREATE INDEX idx_incident_history_incident
ON incident_history(incident_id, cr_dt DESC);

CREATE INDEX idx_incident_history_action
ON incident_history(action);

CREATE INDEX idx_incident_mapping_user
ON incident_mapping(user_id);

CREATE INDEX idx_incident_mapping_vendor
ON incident_mapping(vendor_id);

CREATE INDEX idx_incident_mapping_status
ON incident_mapping(incident_status_id);

CREATE INDEX idx_incident_created_by
ON incident(created_by);



-- ============================================
-- 8. Master data
-- ============================================


INSERT INTO incident_status (status_code, status_desc)
VALUES
('OPEN', 'Incident created'),
('ASSIGNED', 'Assigned to vendor'),
('IN_PROGRESS', 'Work in progress'),
('PENDING', 'Waiting for information or action'),
('RESOLVED', 'Issue resolved'),
('CLOSED', 'Incident closed'),
('REOPENED', 'Incident reopened');


INSERT INTO incident_type (type_code, incidentdesc)
VALUES
('HARDWARE', 'Hardware related'),
('SOFTWARE', 'Software related'),
('NETWORK', 'Network related'),
('SECURITY', 'Security related'),
('CIVIL','Civil works related'),
('OTHER', 'Other incidents');
