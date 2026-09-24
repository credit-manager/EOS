"""Globalization Engine service."""
from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    Country,
    CountryPack,
    Currency,
    ExchangeRate,
    FiscalPeriod,
    NumberingSequence,
    TaxConfig,
)


class GlobalizationService:
    def __init__(self, db: Session):
        self.db = db

    def create_country(self, data: dict) -> Country:
        country = Country(**data)
        self.db.add(country)
        self.db.commit()
        self.db.refresh(country)
        return country

    def get_country(self, code: str) -> Country | None:
        return self.db.query(Country).filter(Country.code == code.upper()).first()

    def list_countries(self, limit: int = 50) -> list[Country]:
        return self.db.query(Country).filter(Country.is_active).order_by(Country.name).limit(limit).all()

    def create_country_pack(self, data: dict) -> CountryPack:
        pack = CountryPack(**data)
        self.db.add(pack)
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def get_country_pack(self, country_code: str) -> CountryPack | None:
        return (
            self.db.query(CountryPack)
            .filter(CountryPack.country_code == country_code.upper(), CountryPack.is_active)
            .first()
        )

    def list_country_packs(self, limit: int = 50) -> list[CountryPack]:
        return self.db.query(CountryPack).filter(CountryPack.is_active).order_by(CountryPack.country_code).limit(limit).all()

    def create_currency(self, data: dict) -> Currency:
        currency = Currency(**data)
        self.db.add(currency)
        self.db.commit()
        self.db.refresh(currency)
        return currency

    def get_currency(self, code: str) -> Currency | None:
        return self.db.query(Currency).filter(Currency.code == code.upper()).first()

    def list_currencies(self, limit: int = 50) -> list[Currency]:
        return self.db.query(Currency).filter(Currency.is_active).order_by(Currency.code).limit(limit).all()

    def create_exchange_rate(self, data: dict) -> ExchangeRate:
        rate = ExchangeRate(**data)
        self.db.add(rate)
        self.db.commit()
        self.db.refresh(rate)
        return rate

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> ExchangeRate | None:
        return (
            self.db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency == from_currency.upper(),
                ExchangeRate.to_currency == to_currency.upper(),
                ExchangeRate.is_active,
            )
            .order_by(ExchangeRate.rate_date.desc())
            .first()
        )

    def list_exchange_rates(self, from_currency: str | None = None, limit: int = 50) -> list[ExchangeRate]:
        q = self.db.query(ExchangeRate).filter(ExchangeRate.is_active)
        if from_currency:
            q = q.filter(ExchangeRate.from_currency == from_currency.upper())
        return q.order_by(ExchangeRate.rate_date.desc()).limit(limit).all()

    def convert_amount(self, amount: int, from_currency: str, to_currency: str) -> dict | None:
        if from_currency.upper() == to_currency.upper():
            return {"amount": amount, "from_currency": from_currency, "to_currency": to_currency, "rate": 1}
        rate = self.get_exchange_rate(from_currency, to_currency)
        if not rate:
            return None
        converted = int(amount * rate.rate / 100)
        return {
            "amount": converted,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate.rate,
            "rate_date": rate.rate_date.isoformat(),
        }

    def create_tax_config(self, data: dict) -> TaxConfig:
        tax = TaxConfig(**data)
        self.db.add(tax)
        self.db.commit()
        self.db.refresh(tax)
        return tax

    def get_tax_configs(self, country_code: str) -> list[TaxConfig]:
        return (
            self.db.query(TaxConfig)
            .filter(TaxConfig.country_code == country_code.upper(), TaxConfig.is_active)
            .order_by(TaxConfig.tax_type)
            .all()
        )

    def create_numbering_sequence(self, tenant_id: str, data: dict) -> NumberingSequence:
        seq = NumberingSequence(tenant_id=tenant_id, **data)
        self.db.add(seq)
        self.db.commit()
        self.db.refresh(seq)
        return seq

    def get_next_number(self, tenant_id: str, entity_type: str) -> str | None:
        seq = (
            self.db.query(NumberingSequence)
            .filter(
                NumberingSequence.tenant_id == tenant_id,
                NumberingSequence.entity_type == entity_type,
                NumberingSequence.is_active,
            )
            .first()
        )
        if not seq:
            return None

        value = seq.next_value
        seq.next_value += 1
        self.db.commit()

        parts = []
        if seq.prefix:
            parts.append(seq.prefix)
        parts.append(str(value).zfill(seq.padding))
        if seq.suffix:
            parts.append(seq.suffix)

        return "".join(parts)

    def list_numbering_sequences(self, tenant_id: str) -> list[NumberingSequence]:
        return (
            self.db.query(NumberingSequence)
            .filter(NumberingSequence.tenant_id == tenant_id)
            .order_by(NumberingSequence.entity_type)
            .all()
        )

    def create_fiscal_period(self, tenant_id: str, data: dict) -> FiscalPeriod:
        period = FiscalPeriod(tenant_id=tenant_id, **data)
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def list_fiscal_periods(self, tenant_id: str, fiscal_year: int | None = None) -> list[FiscalPeriod]:
        q = self.db.query(FiscalPeriod).filter(FiscalPeriod.tenant_id == tenant_id)
        if fiscal_year:
            q = q.filter(FiscalPeriod.fiscal_year == fiscal_year)
        return q.order_by(FiscalPeriod.start_date).all()

    def close_fiscal_period(self, period_id: str, tenant_id: str, closed_by: str) -> FiscalPeriod | None:
        period = (
            self.db.query(FiscalPeriod)
            .filter(FiscalPeriod.id == period_id, FiscalPeriod.tenant_id == tenant_id)
            .first()
        )
        if not period or period.is_closed:
            return None
        period.is_closed = True
        period.closed_at = datetime.utcnow()
        period.closed_by = closed_by
        self.db.commit()
        self.db.refresh(period)
        return period

    def calculate_tax(
        self, *, country_code: str, tax_type: str, subtotal: int, tax_region: str | None = None
    ) -> dict | None:
        """Calculate tax for a given country, type, and subtotal."""
        configs = self.get_tax_configs(country_code)
        matched = [c for c in configs if c.tax_type == tax_type]
        if not matched:
            return None

        config = matched[0]
        rate = config.rate / 100 if config.rate else 0
        tax_amount = int(subtotal * rate)
        total = subtotal + tax_amount

        return {
            "country_code": country_code,
            "tax_type": tax_type,
            "tax_name": config.name,
            "rate": config.rate,
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total": total,
            "tax_region": tax_region or "",
            "is_inclusive": config.is_inclusive,
        }

    def calculate_taxes(
        self, *, country_code: str, items: list[dict], tax_region: str | None = None
    ) -> dict:
        """Calculate taxes for a list of line items."""
        from collections import defaultdict
        results_by_type: dict[str, dict] = defaultdict(lambda: {"subtotal": 0, "tax_amount": 0})
        total_subtotal = 0
        total_tax = 0

        for item in items:
            tax_type = item.get("tax_type", "vat")
            amount = item.get("amount", 0)
            result = self.calculate_tax(
                country_code=country_code, tax_type=tax_type, subtotal=amount, tax_region=tax_region
            )
            if result:
                results_by_type[tax_type]["subtotal"] += result["subtotal"]
                results_by_type[tax_type]["tax_amount"] += result["tax_amount"]
                results_by_type[tax_type]["rate"] = result["rate"]
                results_by_type[tax_type]["tax_name"] = result["tax_name"]
                total_subtotal += result["subtotal"]
                total_tax += result["tax_amount"]

        return {
            "country_code": country_code,
            "tax_region": tax_region or "",
            "total_subtotal": total_subtotal,
            "total_tax": total_tax,
            "grand_total": total_subtotal + total_tax,
            "breakdown": dict(results_by_type),
        }
