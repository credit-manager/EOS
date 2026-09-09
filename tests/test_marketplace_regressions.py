from unittest.mock import MagicMock

import pytest

from core.marketplace_engine import MarketplaceEngine


def test_marketplace_payload_rejects_unknown_top_level_keys():
    with pytest.raises(ValueError, match="Unsupported marketplace payload"):
        MarketplaceEngine._validate_payload({"modules": [], "execute": "danger"})


def test_marketplace_install_requires_published_and_free_item():
    db = MagicMock()
    engine = MarketplaceEngine(db)

    engine.get_item = MagicMock(return_value=None)
    assert engine.install_item("tenant-a", "hidden-item", "user-a")["success"] is False

    engine.get_item.return_value = {
        "item_code": "paid-pack",
        "is_free": False,
        "payload": {},
    }
    result = engine.install_item("tenant-a", "paid-pack", "user-a")
    assert result["success"] is False
    assert "entitlement" in result["error"]
    db.execute.assert_not_called()


def test_marketplace_list_query_only_returns_published_items():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = []

    MarketplaceEngine(db).list_items(limit=50)
    statement, params = db.execute.call_args.args
    assert "is_published = true" in str(statement)
    assert params["lim"] == 50
