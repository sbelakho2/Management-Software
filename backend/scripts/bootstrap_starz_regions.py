import asyncio
import sys
import os
from datetime import date
from decimal import Decimal

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from sqlalchemy import select

from sensei.core.database import async_session_factory
from sensei.models.site import Site
from sensei.models.finance import TaxJurisdiction, TaxRate
from sensei.services.core.site_service import SiteService
from sensei.services.finance.tax_service import TaxService
from sensei.services.finance.currency_settings import CurrencySettingsService
from sensei.services.document_regional import (
    REGIONAL_CONFIGS,
    Region,
    MA_TVA_RATES,
    TN_TVA_RATES,
    WY_SALES_TAX_RATES,
)


def _site_seed_data() -> list[dict]:
    return [
        {
            "site_code": "MA-TNG",
            "name": "Starz Morocco - Tangier",
            "timezone": "Africa/Casablanca",
            "country": "Morocco",
            "address": REGIONAL_CONFIGS[Region.MOROCCO].address,
            "default_currency": REGIONAL_CONFIGS[Region.MOROCCO].currency.value,
            "metadata_json": {
                "region": Region.MOROCCO.value,
                "language": REGIONAL_CONFIGS[Region.MOROCCO].language,
                "entity_name": REGIONAL_CONFIGS[Region.MOROCCO].entity_name,
            },
        },
        {
            "site_code": "TN-BIZ",
            "name": "Starz Tunisia - Bizerte",
            "timezone": "Africa/Tunis",
            "country": "Tunisia",
            "address": REGIONAL_CONFIGS[Region.TUNISIA].address,
            "default_currency": REGIONAL_CONFIGS[Region.TUNISIA].currency.value,
            "metadata_json": {
                "region": Region.TUNISIA.value,
                "language": REGIONAL_CONFIGS[Region.TUNISIA].language,
                "entity_name": REGIONAL_CONFIGS[Region.TUNISIA].entity_name,
            },
        },
        {
            "site_code": "US-WY-CHE",
            "name": "Starz USA - Cheyenne",
            "timezone": "America/Denver",
            "country": "United States",
            "address": REGIONAL_CONFIGS[Region.WYOMING_US].address,
            "default_currency": REGIONAL_CONFIGS[Region.WYOMING_US].currency.value,
            "metadata_json": {
                "region": Region.WYOMING_US.value,
                "language": REGIONAL_CONFIGS[Region.WYOMING_US].language,
                "entity_name": REGIONAL_CONFIGS[Region.WYOMING_US].entity_name,
                "state": "Wyoming",
            },
        },
    ]


def _jurisdiction_seed_data() -> list[dict]:
    return [
        {
            "code": "MA-VAT",
            "name": "Morocco TVA",
            "country": "Morocco",
            "region": None,
            "status": "active",
        },
        {
            "code": "TN-VAT",
            "name": "Tunisia TVA",
            "country": "Tunisia",
            "region": None,
            "status": "active",
        },
        {
            "code": "US-WY-SALES",
            "name": "US Wyoming Sales Tax",
            "country": "United States",
            "region": "Wyoming",
            "status": "active",
        },
    ]


def _rate_seed_data() -> list[dict]:
    effective = date(2026, 1, 1)
    return [
        {
            "jurisdiction_code": "MA-VAT",
            "tax_type": "tva_ma",
            "rate": MA_TVA_RATES["standard"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "MA-VAT",
            "tax_type": "tva_ma_reduced_14",
            "rate": MA_TVA_RATES["reduced_14"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "MA-VAT",
            "tax_type": "tva_ma_reduced_10",
            "rate": MA_TVA_RATES["reduced_10"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "MA-VAT",
            "tax_type": "tva_ma_reduced_7",
            "rate": MA_TVA_RATES["reduced_7"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "MA-VAT",
            "tax_type": "tva_ma_exempt",
            "rate": MA_TVA_RATES["exempt"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "TN-VAT",
            "tax_type": "tva_tn",
            "rate": TN_TVA_RATES["standard"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "TN-VAT",
            "tax_type": "tva_tn_reduced_13",
            "rate": TN_TVA_RATES["reduced_13"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "TN-VAT",
            "tax_type": "tva_tn_reduced_7",
            "rate": TN_TVA_RATES["reduced_7"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "TN-VAT",
            "tax_type": "tva_tn_exempt",
            "rate": TN_TVA_RATES["exempt"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "US-WY-SALES",
            "tax_type": "sales_tax_wy_state",
            "rate": WY_SALES_TAX_RATES["state"].rate,
            "effective_date": effective,
            "status": "active",
        },
        {
            "jurisdiction_code": "US-WY-SALES",
            "tax_type": "sales_tax_wy_laramie",
            "rate": WY_SALES_TAX_RATES["laramie_county"].rate,
            "effective_date": effective,
            "status": "active",
        },
    ]


async def _ensure_sites(db) -> None:
    svc = SiteService(db)
    for payload in _site_seed_data():
        result = await db.execute(select(Site).where(Site.site_code == payload["site_code"]))
        site = result.scalar_one_or_none()
        if site:
            await svc.update_site(site, **payload)
        else:
            await svc.create_site(**payload)


async def _ensure_currency_settings(db) -> None:
    svc = CurrencySettingsService(db)
    settings = await svc.get_settings()
    allowed = set(settings.allowed_currencies or [])
    allowed.update(["MAD", "TND", "USD"])
    await svc.update_settings(
        settings,
        allowed_currencies=sorted(allowed),
        reporting_currency=settings.reporting_currency or "USD",
        auto_update_rates=settings.auto_update_rates,
    )


async def _ensure_jurisdictions_and_rates(db) -> None:
    tax_svc = TaxService(db)

    jurisdictions: dict[str, TaxJurisdiction] = {}
    for payload in _jurisdiction_seed_data():
        result = await db.execute(select(TaxJurisdiction).where(TaxJurisdiction.code == payload["code"]))
        jurisdiction = result.scalar_one_or_none()
        if jurisdiction:
            jurisdiction.name = payload["name"]
            jurisdiction.country = payload["country"]
            jurisdiction.region = payload["region"]
            jurisdiction.status = payload["status"]
        else:
            jurisdiction = await tax_svc.create_jurisdiction(**payload)
        jurisdictions[payload["code"]] = jurisdiction

    for payload in _rate_seed_data():
        jurisdiction = jurisdictions[payload["jurisdiction_code"]]
        result = await db.execute(
            select(TaxRate).where(
                TaxRate.jurisdiction_id == jurisdiction.id,
                TaxRate.tax_type == payload["tax_type"],
                TaxRate.effective_date == payload["effective_date"],
            )
        )
        rate = result.scalar_one_or_none()
        if rate:
            rate.rate = Decimal(payload["rate"])
            rate.status = payload["status"]
        else:
            await tax_svc.create_rate(
                jurisdiction_id=jurisdiction.id,
                tax_type=payload["tax_type"],
                rate=payload["rate"],
                effective_date=payload["effective_date"],
                status=payload["status"],
            )


async def main() -> None:
    async with async_session_factory() as db:
        print("Seeding Starz regional configuration...")
        await _ensure_sites(db)
        await _ensure_currency_settings(db)
        await _ensure_jurisdictions_and_rates(db)
        await db.commit()
        print("Starz regional configuration seeded successfully")


if __name__ == "__main__":
    asyncio.run(main())
