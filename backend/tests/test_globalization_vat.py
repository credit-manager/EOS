"""
VAT calculation tests for Egypt and Saudi Arabia country packs.

Verifies that:
- Egypt VAT (14% standard, 5% reduced, 0% exempt/zero) calculates correctly
- Saudi VAT (15% standard, 0% exempt/zero) calculates correctly
- Both packs integrate via the centralized pack registry
"""

from __future__ import annotations

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.globalization.pack_registry import (
    get_pack_instance,
    initialize_pack,
    get_pack_metadata,
    get_all_pack_metadata,
    list_packs,
    get_supported_countries,
    get_pack_info,
)
from backend.app.globalization.models import Base as GlobalizationBase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db() -> Session:
    """Fresh in-memory SQLite session with globalization tables."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    GlobalizationBase.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# General registry tests
# ---------------------------------------------------------------------------

class TestPackRegistry:
    """Verify the centralized pack registry is populated correctly."""

    def test_supported_countries_include_eg_and_sa(self) -> None:
        countries = get_supported_countries()
        assert "EG" in countries
        assert "SA" in countries

    def test_get_all_pack_metadata_returns_both_packs(self) -> None:
        metadata = get_all_pack_metadata()
        codes = {m["country_code"] for m in metadata}
        assert "EG" in codes
        assert "SA" in codes

    def test_list_packs_returns_both(self) -> None:
        packs = list_packs()
        codes = {p["country_code"] for p in packs}
        assert "EG" in codes
        assert "SA" in codes

    def test_get_pack_info_for_known_code(self) -> None:
        info = get_pack_info("EG")
        assert info is not None
        assert info["country_code"] == "EG"
        assert info["name"] == "Egypt Pack"
        assert info["vat_rate"] == 14.0

    def test_get_pack_info_for_unknown_code_returns_none(self) -> None:
        info = get_pack_info("ZZ")
        assert info is None

    def test_eg_metadata_matches_expected_values(self) -> None:
        meta = get_pack_metadata("EG")
        assert meta is not None
        assert meta["currency"] == "EGP"
        assert meta["language"] == "ar"
        assert meta["timezone"] == "Africa/Cairo"
        assert meta["e_invoice_standard"] == "ETA"

    def test_sa_metadata_matches_expected_values(self) -> None:
        meta = get_pack_metadata("SA")
        assert meta is not None
        assert meta["currency"] == "SAR"
        assert meta["language"] == "ar"
        assert meta["timezone"] == "Asia/Riyadh"
        assert meta["vat_rate"] == 15.0
        assert meta["e_invoice_standard"] == "ZATCA Fatoora"


# ---------------------------------------------------------------------------
# Egypt VAT tests
# ---------------------------------------------------------------------------

class TestEgyptVAT:
    """Verify Egypt VAT calculation via pack instance."""

    def test_eg_standard_vat_14_percent(self, db: Session) -> None:
        svc = get_pack_instance("EG", db)
        result = svc.calculate_vat(1000.0, "standard")
        assert result["taxable_amount"] == 1000.0
        assert result["vat_rate"] == 14.0
        assert result["vat_amount"] == 140.0
        assert result["total_amount"] == 1140.0
        assert result["category"] == "standard"

    def test_eg_reduced_vat_5_percent(self, db: Session) -> None:
        svc = get_pack_instance("EG", db)
        result = svc.calculate_vat(1000.0, "reduced")
        assert result["vat_rate"] == 5.0
        assert result["vat_amount"] == 50.0
        assert result["total_amount"] == 1050.0

    def test_eg_zero_rate_exports(self, db: Session) -> None:
        svc = get_pack_instance("EG", db)
        result = svc.calculate_vat(1000.0, "exported_goods")
        assert result["vat_rate"] == 0.0
        assert result["vat_amount"] == 0.0
        assert result["total_amount"] == 1000.0

    def test_eg_exempt_category(self, db: Session) -> None:
        svc = get_pack_instance("EG", db)
        result = svc.calculate_vat(1000.0, "medical_services")
        assert result["vat_rate"] == 0.0
        assert result["vat_amount"] == 0.0

    def test_eg_zero_amount(self, db: Session) -> None:
        svc = get_pack_instance("EG", db)
        result = svc.calculate_vat(0.0, "standard")
        assert result["vat_amount"] == 0.0
        assert result["total_amount"] == 0.0

    def test_eg_large_amount_precision(self, db: Session) -> None:
        svc = get_pack_instance("EG", db)
        result = svc.calculate_vat(999999.99, "standard")
        assert result["total_amount"] == round(999999.99 * 1.14, 2)

    def test_eg_return_metadata(self, db: Session) -> None:
        """Verify Egypt pack can produce VAT return metadata."""
        svc = get_pack_instance("EG", db)
        cal = svc.calculate_vat(50000.0, "standard")
        assert cal["country_code"] == "EG"
        assert cal["currency"] == "EGP"


# ---------------------------------------------------------------------------
# Saudi VAT tests
# ---------------------------------------------------------------------------

class TestSaudiVAT:
    """Verify Saudi Arabia VAT calculation via pack instance."""

    def test_sa_standard_vat_15_percent(self, db: Session) -> None:
        svc = get_pack_instance("SA", db)
        result = svc.calculate_vat(1000.0, "standard")
        assert result["taxable_amount"] == 1000.0
        assert result["vat_rate"] == 15.0
        assert result["vat_amount"] == 150.0
        assert result["total_amount"] == 1150.0
        assert result["category"] == "standard"

    def test_sa_zero_rate_exports(self, db: Session) -> None:
        svc = get_pack_instance("SA", db)
        result = svc.calculate_vat(1000.0, "exported_goods")
        assert result["vat_rate"] == 0.0
        assert result["vat_amount"] == 0.0
        assert result["total_amount"] == 1000.0

    def test_sa_exempt_category(self, db: Session) -> None:
        svc = get_pack_instance("SA", db)
        result = svc.calculate_vat(1000.0, "financial_services")
        assert result["vat_rate"] == 0.0
        assert result["vat_amount"] == 0.0

    def test_sa_zero_amount(self, db: Session) -> None:
        svc = get_pack_instance("SA", db)
        result = svc.calculate_vat(0.0, "standard")
        assert result["vat_amount"] == 0.0
        assert result["total_amount"] == 0.0

    def test_sa_large_amount_precision(self, db: Session) -> None:
        svc = get_pack_instance("SA", db)
        result = svc.calculate_vat(999999.99, "standard")
        assert result["total_amount"] == round(999999.99 * 1.15, 2)

    def test_sa_return_metadata(self, db: Session) -> None:
        """Verify KSA pack can produce VAT return metadata."""
        svc = get_pack_instance("SA", db)
        cal = svc.calculate_vat(50000.0, "standard")
        assert cal["country_code"] == "SA"
        assert cal["currency"] == "SAR"


# ---------------------------------------------------------------------------
# Cross-pack consistency
# ---------------------------------------------------------------------------

class TestCrossPackConsistency:
    """Verify both packs behave consistently through the registry."""

    def test_both_packs_calculate_vat_for_same_base(self, db: Session) -> None:
        eg = get_pack_instance("EG", db).calculate_vat(1000.0, "standard")
        sa = get_pack_instance("SA", db).calculate_vat(1000.0, "standard")
        assert eg["taxable_amount"] == sa["taxable_amount"] == 1000.0
        assert eg["vat_amount"] == 140.0
        assert sa["vat_amount"] == 150.0
        assert eg["total_amount"] == 1140.0
        assert sa["total_amount"] == 1150.0

    def test_both_packs_recognize_exported_goods_as_zero(self, db: Session) -> None:
        eg = get_pack_instance("EG", db).calculate_vat(100.0, "exported_goods")
        sa = get_pack_instance("SA", db).calculate_vat(100.0, "exported_goods")
        assert eg["vat_rate"] == sa["vat_rate"] == 0.0
        assert eg["vat_amount"] == sa["vat_amount"] == 0.0

    def test_initialize_pack_is_idempotent(self, db: Session) -> None:
        """Calling initialize_pack twice produces the same result."""
        r1 = initialize_pack("EG", db)
        r2 = initialize_pack("EG", db)
        assert r1["status"] == r2["status"] == "initialized"
        assert r1["country"].code == r2["country"].code == "EG"
