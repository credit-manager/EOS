"""Harden inventory tables with database-enforced tenant isolation.

Revision ID: 20260906_harden_inventory_tenant_scope
Revises: 20260908_canonical_tenant_defaults
"""

from alembic import op

revision = "20260906_harden_inventory_tenant_scope"
down_revision = "20260908_canonical_tenant_defaults"
branch_labels = None
depends_on = None

_INVENTORY_TABLES = ("products", "warehouses", "stock_movements")


def upgrade() -> None:
    for table in _INVENTORY_TABLES:
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36)"
        )

    op.execute(
        """
        DO $$
        DECLARE
            tenant_count integer;
            null_rows bigint;
            row_count bigint;
            fallback_tenant text;
            tbl text;
        BEGIN
            SELECT count(*), min(id::text) INTO tenant_count, fallback_tenant
            FROM tenants;

            FOREACH tbl IN ARRAY ARRAY['products','warehouses','stock_movements'] LOOP
                EXECUTE format('SELECT count(*) FROM %I', tbl) INTO row_count;
                EXECUTE format('SELECT count(*) FROM %I WHERE tenant_id IS NULL', tbl) INTO null_rows;

                IF null_rows > 0 THEN
                    IF tenant_count <> 1 THEN
                        IF tenant_count = 0 THEN
                            RAISE EXCEPTION 'Inventory migration blocked: table % contains % rows without tenant_id and no tenant exists', tbl, null_rows;
                        ELSE
                            RAISE EXCEPTION 'Inventory migration blocked: table % contains % rows without tenant_id across % tenants; ownership mapping is required', tbl, null_rows, tenant_count;
                        END IF;
                    END IF;
                    EXECUTE format('UPDATE %I SET tenant_id = $1 WHERE tenant_id IS NULL', tbl)
                    USING fallback_tenant;
                END IF;

                EXECUTE format('ALTER TABLE %I ALTER COLUMN tenant_id SET NOT NULL', tbl);
            END LOOP;
        END $$;
        """
    )

    for table in _INVENTORY_TABLES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table} (tenant_id)"
        )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'products_tenant_id_fkey'
            ) THEN
                ALTER TABLE products
                    ADD CONSTRAINT products_tenant_id_fkey
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'warehouses_tenant_id_fkey'
            ) THEN
                ALTER TABLE warehouses
                    ADD CONSTRAINT warehouses_tenant_id_fkey
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'stock_movements_tenant_id_fkey'
            ) THEN
                ALTER TABLE stock_movements
                    ADD CONSTRAINT stock_movements_tenant_id_fkey
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id);
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        DECLARE
            tbl text;
            policy_name text;
        BEGIN
            FOREACH tbl IN ARRAY ARRAY['products','warehouses','stock_movements'] LOOP
                policy_name := 'tenant_isolation_' || tbl;
                EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
                EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY', tbl);
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, tbl);
                EXECUTE format(
                    'CREATE POLICY %I ON %I USING (tenant_id::text = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
                    policy_name, tbl
                );
            END LOOP;
        END $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION eos_inventory_set_tenant_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.tenant_id IS NULL THEN
                NEW.tenant_id := NULLIF(current_setting('app.tenant_id', true), '')::varchar(36);
            END IF;
            IF NEW.tenant_id IS NULL THEN
                RAISE EXCEPTION 'tenant context is required for inventory writes';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    for table in _INVENTORY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_tenant_id ON {table}")
        op.execute(
            f"CREATE TRIGGER trg_{table}_tenant_id BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION eos_inventory_set_tenant_id()"
        )


def downgrade() -> None:
    for table in _INVENTORY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_tenant_id ON {table}")
    op.execute("DROP FUNCTION IF EXISTS eos_inventory_set_tenant_id()")
    for table in _INVENTORY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_tenant_id_fkey")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_tenant_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id")
