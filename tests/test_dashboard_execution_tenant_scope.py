from unittest.mock import MagicMock, patch

from core.analytics_engine import AnalyticsEngine, _execute_query


def test_execute_dashboard_accepts_tenant_scope():
    db = MagicMock()
    row = MagicMock()
    row.__getitem__.side_effect = lambda k: {"id": "d1", "dashboard_name": "D", "dashboard_type": "kpi"}[k]
    db.execute.return_value.mappings.return_value.first.return_value = row
    db.execute.return_value.fetchall.return_value = []
    result = AnalyticsEngine(db).execute_dashboard("d1", tenant_id="tenant-a")
    assert result["id"] == "d1"
    params = db.execute.call_args_list[0].args[1]
    assert params["tid"] == "tenant-a"


def test_analytics_query_binds_tenant_instead_of_interpolating():
    db = MagicMock()
    db.execute.return_value = []
    with patch("core.analytics_engine.SessionLocal", return_value=db):
        _execute_query("SELECT * FROM dbp_customers WHERE tenant_id = 'tenant-a'", tenant_id="tenant-a")
    statement = str(db.execute.call_args.args[0])
    params = db.execute.call_args.args[1]
    assert "tenant_id = :_tid" in statement
    assert "tenant-a" not in statement
    assert params["_tid"] == "tenant-a"
