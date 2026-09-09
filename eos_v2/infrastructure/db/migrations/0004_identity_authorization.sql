-- EOS DBP v2 migration 0004: tenant identity and authorization persistence.
-- Apply only to the dedicated v2 database/schema. Never execute against the legacy database.

CREATE TABLE IF NOT EXISTS eos_v2_tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS eos_v2_actors (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES eos_v2_tenants(id),
    subject VARCHAR(255) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_eos_v2_actor_subject UNIQUE (tenant_id, subject)
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_actors_tenant
    ON eos_v2_actors (tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_roles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES eos_v2_tenants(id),
    name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_eos_v2_role_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_roles_tenant
    ON eos_v2_roles (tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_actor_roles (
    actor_id UUID NOT NULL REFERENCES eos_v2_actors(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES eos_v2_roles(id) ON DELETE CASCADE,
    PRIMARY KEY (actor_id, role_id)
);

CREATE TABLE IF NOT EXISTS eos_v2_role_permissions (
    role_id UUID NOT NULL REFERENCES eos_v2_roles(id) ON DELETE CASCADE,
    permission VARCHAR(50) NOT NULL,
    PRIMARY KEY (role_id, permission),
    CONSTRAINT ck_eos_v2_permission_value CHECK (permission IN ('read', 'write', 'admin'))
);
