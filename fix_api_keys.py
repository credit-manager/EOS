from database import engine
from sqlalchemy import text
with engine.begin() as conn:
    conn.execute(text('DROP TABLE IF EXISTS dbp_api_keys CASCADE'))
    conn.execute(text("""CREATE TABLE dbp_api_keys (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        company_id VARCHAR(36),
        key_name VARCHAR(100),
        key_hash VARCHAR(200) NOT NULL,
        name VARCHAR(200),
        permissions TEXT,
        rate_limit_read INT DEFAULT 200,
        rate_limit_write INT DEFAULT 50,
        expires_at TIMESTAMPTZ,
        is_active BOOLEAN DEFAULT true,
        last_used_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )"""))
    conn.execute(text('CREATE INDEX idx_dbp_api_keys_tenant ON dbp_api_keys(tenant_id, is_active)'))
    conn.execute(text('CREATE INDEX idx_dbp_api_keys_hash ON dbp_api_keys(key_hash)'))
    print('Merged dbp_api_keys table created OK')
