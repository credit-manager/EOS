from unittest.mock import MagicMock

import pytest

from core.builder_engine import BuilderEngine, FIELD_SQL_TYPES, RESERVED_FIELD_CODES


def test_builder_rejects_reserved_system_columns():
    db = MagicMock()
    engine = BuilderEngine(db)
    with pytest.raises(ValueError, match="Reserved field code"):
        engine._ensure_physical_table(
            "bld_customer",
            [{"code": "tenant_id", "field_type": "string"}],
        )
    db.execute.assert_not_called()


def test_builder_delegates_physical_ddl_to_database_function():
    db = MagicMock()
    engine = BuilderEngine(db)
    engine._ensure_physical_table(
        "bld_customer",
        [{"code": "name", "field_type": "string", "is_required": True}],
    )
    statement, params = db.execute.call_args.args
    assert "eos_create_builder_table" in str(statement)
    assert params["table_name"] == "bld_customer"
    assert "VARCHAR(255)" in params["columns"]
    assert '"not_null": true' in params["columns"]


def test_builder_sql_type_catalog_is_closed():
    assert set(FIELD_SQL_TYPES) == {
        "string", "text", "integer", "float", "number", "boolean",
        "date", "datetime", "enum", "json",
    }
    assert RESERVED_FIELD_CODES == {"id", "tenant_id", "created_at"}
