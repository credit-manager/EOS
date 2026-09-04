from unittest.mock import MagicMock
import pytest
from routers.dashboards import get_dashboard, delete_dashboard, list_widgets, delete_widget

@pytest.mark.asyncio
async def test_get_dashboard_rejects_foreign_tenant():
    db=MagicMock(); db.execute.return_value.fetchone.return_value=None
    with pytest.raises(Exception) as exc:
        await get_dashboard('dash-b', {'tenant_id':'tenant-a'}, db)
    assert getattr(exc.value, 'status_code', None) == 404

@pytest.mark.asyncio
async def test_delete_dashboard_is_tenant_scoped():
    db=MagicMock(); db.execute.return_value.rowcount=0
    with pytest.raises(Exception) as exc:
        await delete_dashboard('dash-b', {'tenant_id':'tenant-a'}, db)
    assert getattr(exc.value, 'status_code', None) == 404

@pytest.mark.asyncio
async def test_list_widgets_rejects_foreign_dashboard():
    db=MagicMock(); db.execute.return_value.fetchone.return_value=None
    with pytest.raises(Exception) as exc:
        await list_widgets('dash-b', {'tenant_id':'tenant-a'}, db)
    assert getattr(exc.value, 'status_code', None) == 404

@pytest.mark.asyncio
async def test_delete_widget_requires_tenant_owned_dashboard():
    db=MagicMock(); db.execute.return_value.fetchone.return_value=None
    with pytest.raises(Exception) as exc:
        await delete_widget('dash-b','widget-b', {'tenant_id':'tenant-a'}, db)
    assert getattr(exc.value, 'status_code', None) == 404
