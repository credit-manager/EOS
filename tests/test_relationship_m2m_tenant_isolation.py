from core.relationship_engine import RelationshipEngine


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        if "information_schema.columns" in sql:
            return Result([(1,)])
        return Result([])


def test_m2m_filters_target_and_junction_by_tenant_when_supported():
    db = FakeDB()
    engine = RelationshipEngine(db)

    engine._m2m_rows(
        source_value="source-a",
        target_table="roles",
        target_column="id",
        junction_table="user_roles",
        junction_source_col="user_id",
        junction_target_col="role_id",
        tenant_scope=True,
        tenant_id="tenant-a",
    )

    sql, params = db.calls[-1]
    assert "t.tenant_id = :tenant_id" in sql
    assert "j.tenant_id = :tenant_id" in sql
    assert params == {"source_value": "source-a", "tenant_id": "tenant-a"}


def test_m2m_still_filters_target_when_junction_has_no_tenant_column():
    db = FakeDB()
    engine = RelationshipEngine(db)
    engine._has_tenant_column = lambda table: False

    engine._m2m_rows(
        source_value="source-a",
        target_table="roles",
        target_column="id",
        junction_table="user_roles",
        junction_source_col="user_id",
        junction_target_col="role_id",
        tenant_scope=True,
        tenant_id="tenant-a",
    )

    sql, params = db.calls[-1]
    assert "t.tenant_id = :tenant_id" in sql
    assert "j.tenant_id = :tenant_id" not in sql
    assert params == {"source_value": "source-a", "tenant_id": "tenant-a"}


def test_m2m_identifier_validation_blocks_sql_injection():
    db = FakeDB()
    engine = RelationshipEngine(db)

    try:
        engine._m2m_rows(
            source_value="source-a",
            target_table="roles; DROP TABLE roles;",
            target_column="id",
            junction_table="user_roles",
            junction_source_col="user_id",
            junction_target_col="role_id",
            tenant_scope=True,
            tenant_id="tenant-a",
        )
    except ValueError as exc:
        assert "Invalid target table" in str(exc)
    else:
        raise AssertionError("Unsafe SQL identifier was accepted")
