"""Document Generation Engine + Regional Compliance (Development Plan 22.11-22.12).

Implements:
- Morocco Regional Compliance (ICE, IF, RC, CNSS, TVA, MAD, StarzMLogo.jpg)
- Tunisia Regional Compliance (MF, RC, CD, TVA, TND, StarzLogo.png)
- Wyoming Regional Compliance (Sales Tax, EIN, Workers' Comp, SOS)
- Document Generation with templates and branding
- Logo Asset Registry and Letterhead support
- Immutable Document Binding with SHA256
- Electronic Signature Integration
- Tax/Labor/Safety logic per jurisdiction
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


# ============================================================
# Role Definitions
# ============================================================

_FINANCE_READ_ROLES = frozenset({"admin", "finance", "accountant", "auditor", "ceo"})
_FINANCE_WRITE_ROLES = frozenset({"admin", "finance", "accountant"})
_HR_READ_ROLES = frozenset({"admin", "hr", "auditor", "ceo"})
_HR_WRITE_ROLES = frozenset({"admin", "hr"})
_DOC_GENERATE_ROLES = frozenset({"admin", "finance", "accountant", "ops", "gm"})
_ADMIN_ROLES = frozenset({"admin"})


# ============================================================
# Enums
# ============================================================


class Region(str, Enum):
    """Supported regional jurisdictions."""

    MOROCCO = "MA"
    TUNISIA = "TN"
    WYOMING_US = "US-WY"


class Currency(str, Enum):
    """Regional currencies."""

    MAD = "MAD"  # Moroccan Dirham
    TND = "TND"  # Tunisian Dinar
    USD = "USD"  # US Dollar


class DocumentType(str, Enum):
    """Types of generated documents."""

    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    PACKING_SLIP = "packing_slip"
    COC = "certificate_of_conformance"
    PAYSLIP = "payslip"
    LETTER = "letter"
    REPORT = "report"


class TaxType(str, Enum):
    """Tax types across regions."""

    TVA_MA = "TVA_MA"  # Morocco VAT
    TVA_TN = "TVA_TN"  # Tunisia VAT
    SALES_TAX_WY = "SALES_TAX_WY"  # Wyoming Sales Tax
    WITHHOLDING_TN = "WITHHOLDING_TN"  # Tunisia Retenue à la Source


class SignatureStatus(str, Enum):
    """Electronic signature status."""

    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ============================================================
# Regional Configuration
# ============================================================


@dataclass(frozen=True)
class RegionalConfig:
    """Configuration for a regional entity."""

    region: Region
    entity_name: str
    address: str
    currency: Currency
    logo_asset: str
    language: str
    # Morocco-specific
    ice: str | None = None  # Identifiant Commun de l'Entreprise
    if_code: str | None = None  # Identifiant Fiscal
    rc: str | None = None  # Registre du Commerce
    cnss: str | None = None  # CNSS Number
    # Tunisia-specific
    mf: str | None = None  # Matricule Fiscal
    cd: str | None = None  # Code Douane
    # US/Wyoming-specific
    ein: str | None = None  # Employer Identification Number
    sos_file_number: str | None = None  # Secretary of State file number


REGIONAL_CONFIGS: dict[Region, RegionalConfig] = {
    Region.MOROCCO: RegionalConfig(
        region=Region.MOROCCO,
        entity_name="Starz Morocco SARL",
        address="Tangier Automotive City, Lot 8, Tangier, Morocco",
        currency=Currency.MAD,
        logo_asset="StarzMLogo.jpg",
        language="fr",
        ice="001234567890123",
        if_code="12345678",
        rc="12345",
        cnss="1234567",
    ),
    Region.TUNISIA: RegionalConfig(
        region=Region.TUNISIA,
        entity_name="Starz Tunisia SARL",
        address="3 Rue Hedi Cheker, Bizerte, Tunisia 7000",
        currency=Currency.TND,
        logo_asset="StarzLogo.png",
        language="fr",
        mf="1234567/A/B/M/000",
        rc="B1234567890",
        cd="12345678",
    ),
    Region.WYOMING_US: RegionalConfig(
        region=Region.WYOMING_US,
        entity_name="Starz USA LLC",
        address="1621 Central Ave, Cheyenne, WY 82001, USA",
        currency=Currency.USD,
        logo_asset="StarzLogo.png",
        language="en",
        ein="12-3456789",
        sos_file_number="2023-001234567",
    ),
}


# ============================================================
# Tax Rate Definitions
# ============================================================


@dataclass(frozen=True)
class TaxRate:
    """Tax rate definition."""

    tax_type: TaxType
    rate: Decimal
    description: str


# Morocco TVA rates
MA_TVA_RATES = {
    "standard": TaxRate(TaxType.TVA_MA, Decimal("0.20"), "Standard rate 20%"),
    "reduced_14": TaxRate(TaxType.TVA_MA, Decimal("0.14"), "Reduced rate 14%"),
    "reduced_10": TaxRate(TaxType.TVA_MA, Decimal("0.10"), "Reduced rate 10%"),
    "reduced_7": TaxRate(TaxType.TVA_MA, Decimal("0.07"), "Reduced rate 7%"),
    "exempt": TaxRate(TaxType.TVA_MA, Decimal("0"), "Exonerated"),
}

# Tunisia TVA rates
TN_TVA_RATES = {
    "standard": TaxRate(TaxType.TVA_TN, Decimal("0.19"), "Standard rate 19%"),
    "reduced_13": TaxRate(TaxType.TVA_TN, Decimal("0.13"), "Reduced rate 13%"),
    "reduced_7": TaxRate(TaxType.TVA_TN, Decimal("0.07"), "Reduced rate 7%"),
    "exempt": TaxRate(TaxType.TVA_TN, Decimal("0"), "Exonerated"),
}

# Wyoming Sales Tax rates (State + sample county)
WY_SALES_TAX_RATES = {
    "state": TaxRate(TaxType.SALES_TAX_WY, Decimal("0.04"), "Wyoming State 4%"),
    "laramie_county": TaxRate(TaxType.SALES_TAX_WY, Decimal("0.01"), "Laramie County 1%"),
}


# ============================================================
# Labor/Contribution Definitions
# ============================================================


@dataclass(frozen=True)
class ContributionRate:
    """Social contribution rate."""

    region: Region
    name: str
    employer_rate: Decimal
    employee_rate: Decimal
    cap: Decimal | None = None  # Maximum wage base


# Morocco CNSS/AMO
MA_CONTRIBUTIONS = {
    "cnss_short_term": ContributionRate(
        Region.MOROCCO, "CNSS Short-term", Decimal("0.0426"), Decimal("0.0")
    ),
    "cnss_long_term": ContributionRate(
        Region.MOROCCO, "CNSS Long-term", Decimal("0.0789"), Decimal("0.0")
    ),
    "amo": ContributionRate(
        Region.MOROCCO, "AMO", Decimal("0.0248"), Decimal("0.0227")
    ),
}

# Tunisia CNSS/TFP/FOPROLOS
TN_CONTRIBUTIONS = {
    "cnss": ContributionRate(
        Region.TUNISIA, "CNSS", Decimal("0.1657"), Decimal("0.0918")
    ),
    "tfp": ContributionRate(Region.TUNISIA, "TFP", Decimal("0.01"), Decimal("0")),
    "foprolos": ContributionRate(
        Region.TUNISIA, "FOPROLOS", Decimal("0.01"), Decimal("0")
    ),
}

# Wyoming Workers' Comp / UI
WY_CONTRIBUTIONS = {
    "workers_comp": ContributionRate(
        Region.WYOMING_US, "Workers' Compensation", Decimal("0.015"), Decimal("0")
    ),
    "unemployment": ContributionRate(
        Region.WYOMING_US, "Unemployment Insurance", Decimal("0.024"), Decimal("0")
    ),
}


# ============================================================
# Document Models
# ============================================================


@dataclass(frozen=True)
class LogoAsset:
    """Logo asset in the registry."""

    id: UUID
    filename: str
    content_hash: str
    width_px: int
    height_px: int
    format: str
    created_at: datetime
    is_optimized: bool = False


@dataclass(frozen=True)
class LetterheadTemplate:
    """Letterhead template for formal correspondence."""

    id: UUID
    region: Region
    name: str
    logo_asset_id: UUID
    header_text: str
    footer_text: str
    background_image: str | None = None


@dataclass(frozen=True)
class GeneratedDocument:
    """Generated document with binding and signature."""

    id: UUID
    document_type: DocumentType
    region: Region
    template_name: str
    entity_version_id: UUID
    content_hash: str  # SHA256 of rendered content
    rendered_at: datetime
    generated_by: str
    correlation_id: str
    bound_entity_type: str | None = None
    bound_entity_id: UUID | None = None
    signature_status: SignatureStatus = SignatureStatus.PENDING
    signed_by: str | None = None
    signed_at: datetime | None = None


@dataclass(frozen=True)
class InvoiceData:
    """Invoice content for rendering."""

    invoice_number: str
    invoice_date: date
    due_date: date
    customer_name: str
    customer_address: str
    customer_tax_id: str | None
    line_items: tuple[dict[str, Any], ...]
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    tax_rate_applied: str
    notes: str = ""


@dataclass(frozen=True)
class PayslipData:
    """Payslip content for rendering."""

    employee_id: str
    employee_name: str
    pay_period_start: date
    pay_period_end: date
    gross_salary: Decimal
    contributions: tuple[dict[str, Any], ...]
    net_salary: Decimal
    region: Region


@dataclass(frozen=True)
class SOSReminder:
    """Secretary of State reminder."""

    id: UUID
    region: Region
    reminder_type: str  # annual_report, registered_agent
    due_date: date
    entity_name: str
    sos_file_number: str
    is_completed: bool = False
    completed_at: datetime | None = None


@dataclass
class AuditEntry:
    """Audit log entry."""

    id: UUID
    timestamp: datetime
    actor_id: str
    action: str
    entity_type: str
    entity_id: UUID | None
    correlation_id: str
    details: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Service
# ============================================================


class DocumentRegionalService:
    """Document Generation + Regional Compliance Service."""

    def __init__(self) -> None:
        self._logo_assets: dict[UUID, LogoAsset] = {}
        self._letterheads: dict[UUID, LetterheadTemplate] = {}
        self._documents: dict[UUID, GeneratedDocument] = {}
        self._sos_reminders: dict[UUID, SOSReminder] = {}
        self._audit_log: list[AuditEntry] = []

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _require_doc_generate(self, actor_roles: set[str]) -> None:
        if not actor_roles & _DOC_GENERATE_ROLES:
            raise PermissionError("Document generation access required")

    def _require_admin(self, actor_roles: set[str]) -> None:
        if not actor_roles & _ADMIN_ROLES:
            raise PermissionError("Admin role required")

    def _require_hr_read(self, actor_roles: set[str]) -> None:
        if not actor_roles & _HR_READ_ROLES:
            raise PermissionError("HR read access required")

    def _require_finance_read(self, actor_roles: set[str]) -> None:
        if not actor_roles & _FINANCE_READ_ROLES:
            raise PermissionError("Finance read access required")

    def _audit(
        self,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._audit_log.append(
            AuditEntry(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                details=details or {},
            )
        )

    def _compute_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    # --------------------------------------------------------
    # Logo Asset Registry
    # --------------------------------------------------------

    def register_logo_asset(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        filename: str,
        content: bytes,
        width_px: int,
        height_px: int,
        format: str,
    ) -> LogoAsset:
        """Register a logo asset in the global registry."""
        self._require_admin(actor_roles)

        content_hash = hashlib.sha256(content).hexdigest()

        asset = LogoAsset(
            id=uuid4(),
            filename=filename,
            content_hash=content_hash,
            width_px=width_px,
            height_px=height_px,
            format=format,
            created_at=datetime.now(timezone.utc),
            is_optimized=False,
        )
        self._logo_assets[asset.id] = asset

        self._audit(
            actor_id,
            "logo_asset.register",
            "logo_asset",
            asset.id,
            correlation_id,
            {"filename": filename},
        )
        return asset

    def optimize_logo_asset(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        asset_id: UUID,
    ) -> LogoAsset:
        """Mark a logo asset as optimized for high-resolution PDF embedding."""
        self._require_admin(actor_roles)

        if asset_id not in self._logo_assets:
            raise ValueError(f"Logo asset {asset_id} not found")

        old = self._logo_assets[asset_id]
        optimized = LogoAsset(
            id=old.id,
            filename=old.filename,
            content_hash=old.content_hash,
            width_px=old.width_px,
            height_px=old.height_px,
            format=old.format,
            created_at=old.created_at,
            is_optimized=True,
        )
        self._logo_assets[asset_id] = optimized

        self._audit(
            actor_id,
            "logo_asset.optimize",
            "logo_asset",
            asset_id,
            correlation_id,
        )
        return optimized

    def list_logo_assets(self, actor_roles: set[str]) -> list[LogoAsset]:
        """List all registered logo assets."""
        self._require_doc_generate(actor_roles)
        return list(self._logo_assets.values())

    # --------------------------------------------------------
    # Letterhead Templates
    # --------------------------------------------------------

    def register_letterhead(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        region: Region,
        name: str,
        logo_asset_id: UUID,
        header_text: str,
        footer_text: str,
        background_image: str | None = None,
    ) -> LetterheadTemplate:
        """Register a letterhead template for formal correspondence."""
        self._require_admin(actor_roles)

        if logo_asset_id not in self._logo_assets:
            raise ValueError(f"Logo asset {logo_asset_id} not found")

        template = LetterheadTemplate(
            id=uuid4(),
            region=region,
            name=name,
            logo_asset_id=logo_asset_id,
            header_text=header_text,
            footer_text=footer_text,
            background_image=background_image,
        )
        self._letterheads[template.id] = template

        self._audit(
            actor_id,
            "letterhead.register",
            "letterhead",
            template.id,
            correlation_id,
            {"region": region.value, "name": name},
        )
        return template

    def list_letterheads(
        self, actor_roles: set[str], region: Region | None = None
    ) -> list[LetterheadTemplate]:
        """List letterhead templates, optionally filtered by region."""
        self._require_doc_generate(actor_roles)
        templates = list(self._letterheads.values())
        if region:
            templates = [t for t in templates if t.region == region]
        return templates

    # --------------------------------------------------------
    # Tax Calculations
    # --------------------------------------------------------

    def calculate_tva_morocco(
        self, amount: Decimal, rate_key: str = "standard"
    ) -> tuple[Decimal, Decimal]:
        """Calculate Morocco TVA.

        Returns (tax_amount, total).
        """
        if rate_key not in MA_TVA_RATES:
            raise ValueError(f"Unknown MA TVA rate: {rate_key}")
        rate = MA_TVA_RATES[rate_key].rate
        tax = (amount * rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return tax, amount + tax

    def calculate_tva_tunisia(
        self, amount: Decimal, rate_key: str = "standard"
    ) -> tuple[Decimal, Decimal]:
        """Calculate Tunisia TVA.

        Returns (tax_amount, total).
        """
        if rate_key not in TN_TVA_RATES:
            raise ValueError(f"Unknown TN TVA rate: {rate_key}")
        rate = TN_TVA_RATES[rate_key].rate
        tax = (amount * rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return tax, amount + tax

    def calculate_withholding_tunisia(
        self, amount: Decimal, rate: Decimal = Decimal("0.15")
    ) -> Decimal:
        """Calculate Tunisia Retenue à la Source (withholding tax)."""
        return (amount * rate).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def calculate_sales_tax_wyoming(
        self, amount: Decimal, county: str = "laramie_county"
    ) -> tuple[Decimal, Decimal]:
        """Calculate Wyoming Sales + Use Tax.

        Returns (tax_amount, total).
        """
        state_rate = WY_SALES_TAX_RATES["state"].rate
        county_rate = WY_SALES_TAX_RATES.get(county, WY_SALES_TAX_RATES["state"]).rate
        total_rate = state_rate + county_rate
        tax = (amount * total_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return tax, amount + tax

    # --------------------------------------------------------
    # Labor/Contribution Calculations
    # --------------------------------------------------------

    def calculate_contributions_morocco(
        self, gross_salary: Decimal
    ) -> dict[str, dict[str, Decimal]]:
        """Calculate Morocco CNSS/AMO contributions."""
        result = {}
        for key, contrib in MA_CONTRIBUTIONS.items():
            employer = (gross_salary * contrib.employer_rate).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            employee = (gross_salary * contrib.employee_rate).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            result[key] = {"employer": employer, "employee": employee}
        return result

    def calculate_contributions_tunisia(
        self, gross_salary: Decimal
    ) -> dict[str, dict[str, Decimal]]:
        """Calculate Tunisia CNSS/TFP/FOPROLOS contributions."""
        result = {}
        for key, contrib in TN_CONTRIBUTIONS.items():
            employer = (gross_salary * contrib.employer_rate).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            employee = (gross_salary * contrib.employee_rate).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            result[key] = {"employer": employer, "employee": employee}
        return result

    def calculate_contributions_wyoming(
        self, gross_salary: Decimal
    ) -> dict[str, dict[str, Decimal]]:
        """Calculate Wyoming Workers' Comp and UI contributions."""
        result = {}
        for key, contrib in WY_CONTRIBUTIONS.items():
            employer = (gross_salary * contrib.employer_rate).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            employee = (gross_salary * contrib.employee_rate).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            result[key] = {"employer": employer, "employee": employee}
        return result

    # --------------------------------------------------------
    # Leave Accrual Logic
    # --------------------------------------------------------

    def calculate_leave_accrual_morocco(
        self, months_worked: int, current_balance: Decimal = Decimal("0")
    ) -> Decimal:
        """Calculate Morocco leave accrual (1.5 days/month)."""
        accrual = Decimal("1.5") * months_worked
        return current_balance + accrual

    def calculate_leave_accrual_tunisia(
        self, months_worked: int, current_balance: Decimal = Decimal("0")
    ) -> Decimal:
        """Calculate Tunisia leave accrual (1.5 days/month standard)."""
        accrual = Decimal("1.5") * months_worked
        return current_balance + accrual

    def calculate_leave_accrual_wyoming(
        self, months_worked: int, current_balance: Decimal = Decimal("0")
    ) -> Decimal:
        """Calculate US leave accrual (no federal mandate, typical 1.25 days/month)."""
        accrual = Decimal("1.25") * months_worked
        return current_balance + accrual

    # --------------------------------------------------------
    # Document Generation
    # --------------------------------------------------------

    def generate_invoice(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        region: Region,
        invoice_data: InvoiceData,
        entity_version_id: UUID,
        bound_entity_type: str | None = None,
        bound_entity_id: UUID | None = None,
    ) -> GeneratedDocument:
        """Generate an invoice with regional branding and legal fields."""
        self._require_doc_generate(actor_roles)

        config = REGIONAL_CONFIGS[region]

        # Build document content (simulation)
        content_lines = [
            f"INVOICE: {invoice_data.invoice_number}",
            f"Entity: {config.entity_name}",
            f"Logo: {config.logo_asset}",
            f"Address: {config.address}",
        ]

        if region == Region.MOROCCO:
            content_lines.extend([
                f"ICE: {config.ice}",
                f"IF: {config.if_code}",
                f"RC: {config.rc}",
                f"CNSS: {config.cnss}",
            ])
        elif region == Region.TUNISIA:
            content_lines.extend([
                f"MF: {config.mf}",
                f"RC: {config.rc}",
                f"CD: {config.cd}",
            ])
        elif region == Region.WYOMING_US:
            content_lines.extend([
                f"EIN: {config.ein}",
            ])

        content_lines.extend([
            f"Customer: {invoice_data.customer_name}",
            f"Subtotal: {invoice_data.subtotal} {config.currency.value}",
            f"Tax ({invoice_data.tax_rate_applied}): {invoice_data.tax_amount}",
            f"Total: {invoice_data.total} {config.currency.value}",
        ])

        content = "\n".join(content_lines)
        content_hash = self._compute_hash(content)

        doc = GeneratedDocument(
            id=uuid4(),
            document_type=DocumentType.INVOICE,
            region=region,
            template_name=f"invoice_{region.value.lower()}",
            entity_version_id=entity_version_id,
            content_hash=content_hash,
            rendered_at=datetime.now(timezone.utc),
            generated_by=actor_id,
            correlation_id=correlation_id,
            bound_entity_type=bound_entity_type,
            bound_entity_id=bound_entity_id,
        )
        self._documents[doc.id] = doc

        self._audit(
            actor_id,
            "document.generate",
            "invoice",
            doc.id,
            correlation_id,
            {"region": region.value, "invoice_number": invoice_data.invoice_number},
        )
        return doc

    def generate_payslip(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        payslip_data: PayslipData,
        entity_version_id: UUID,
    ) -> GeneratedDocument:
        """Generate a payslip with regional contribution breakdown."""
        self._require_doc_generate(actor_roles)

        region = payslip_data.region
        config = REGIONAL_CONFIGS[region]

        content_lines = [
            f"PAYSLIP: {payslip_data.employee_name}",
            f"Entity: {config.entity_name}",
            f"Period: {payslip_data.pay_period_start} to {payslip_data.pay_period_end}",
            f"Gross: {payslip_data.gross_salary} {config.currency.value}",
            f"Net: {payslip_data.net_salary} {config.currency.value}",
        ]

        content = "\n".join(content_lines)
        content_hash = self._compute_hash(content)

        doc = GeneratedDocument(
            id=uuid4(),
            document_type=DocumentType.PAYSLIP,
            region=region,
            template_name=f"payslip_{region.value.lower()}",
            entity_version_id=entity_version_id,
            content_hash=content_hash,
            rendered_at=datetime.now(timezone.utc),
            generated_by=actor_id,
            correlation_id=correlation_id,
        )
        self._documents[doc.id] = doc

        self._audit(
            actor_id,
            "document.generate",
            "payslip",
            doc.id,
            correlation_id,
            {"region": region.value, "employee_id": payslip_data.employee_id},
        )
        return doc

    def generate_coc(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        region: Region,
        product_description: str,
        lot_number: str,
        inspection_results: dict[str, str],
        entity_version_id: UUID,
        bound_entity_id: UUID,
    ) -> GeneratedDocument:
        """Generate a Certificate of Conformance."""
        self._require_doc_generate(actor_roles)

        config = REGIONAL_CONFIGS[region]

        content_lines = [
            "CERTIFICATE OF CONFORMANCE",
            f"Entity: {config.entity_name}",
            f"Product: {product_description}",
            f"Lot: {lot_number}",
            "Inspection Results:",
        ]
        for key, val in inspection_results.items():
            content_lines.append(f"  {key}: {val}")

        content = "\n".join(content_lines)
        content_hash = self._compute_hash(content)

        doc = GeneratedDocument(
            id=uuid4(),
            document_type=DocumentType.COC,
            region=region,
            template_name=f"coc_{region.value.lower()}",
            entity_version_id=entity_version_id,
            content_hash=content_hash,
            rendered_at=datetime.now(timezone.utc),
            generated_by=actor_id,
            correlation_id=correlation_id,
            bound_entity_type="lot",
            bound_entity_id=bound_entity_id,
        )
        self._documents[doc.id] = doc

        self._audit(
            actor_id,
            "document.generate",
            "coc",
            doc.id,
            correlation_id,
            {"region": region.value, "lot_number": lot_number},
        )
        return doc

    # --------------------------------------------------------
    # Electronic Signature
    # --------------------------------------------------------

    def request_signature(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        document_id: UUID,
        signer_id: str,
    ) -> GeneratedDocument:
        """Request electronic signature on a document."""
        self._require_doc_generate(actor_roles)

        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")

        # Document stays pending until signed
        self._audit(
            actor_id,
            "signature.request",
            "document",
            document_id,
            correlation_id,
            {"signer_id": signer_id},
        )
        return self._documents[document_id]

    def apply_signature(
        self,
        signer_id: str,
        signer_roles: set[str],
        correlation_id: str,
        document_id: UUID,
    ) -> GeneratedDocument:
        """Apply electronic signature to a document."""
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")

        old = self._documents[document_id]
        if old.signature_status != SignatureStatus.PENDING:
            raise ValueError(f"Document is not pending signature")

        signed = GeneratedDocument(
            id=old.id,
            document_type=old.document_type,
            region=old.region,
            template_name=old.template_name,
            entity_version_id=old.entity_version_id,
            content_hash=old.content_hash,
            rendered_at=old.rendered_at,
            generated_by=old.generated_by,
            correlation_id=old.correlation_id,
            bound_entity_type=old.bound_entity_type,
            bound_entity_id=old.bound_entity_id,
            signature_status=SignatureStatus.SIGNED,
            signed_by=signer_id,
            signed_at=datetime.now(timezone.utc),
        )
        self._documents[document_id] = signed

        self._audit(
            signer_id,
            "signature.apply",
            "document",
            document_id,
            correlation_id,
        )
        return signed

    def reject_signature(
        self,
        signer_id: str,
        signer_roles: set[str],
        correlation_id: str,
        document_id: UUID,
        reason: str,
    ) -> GeneratedDocument:
        """Reject signing a document."""
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")

        old = self._documents[document_id]
        if old.signature_status != SignatureStatus.PENDING:
            raise ValueError(f"Document is not pending signature")

        rejected = GeneratedDocument(
            id=old.id,
            document_type=old.document_type,
            region=old.region,
            template_name=old.template_name,
            entity_version_id=old.entity_version_id,
            content_hash=old.content_hash,
            rendered_at=old.rendered_at,
            generated_by=old.generated_by,
            correlation_id=old.correlation_id,
            bound_entity_type=old.bound_entity_type,
            bound_entity_id=old.bound_entity_id,
            signature_status=SignatureStatus.REJECTED,
        )
        self._documents[document_id] = rejected

        self._audit(
            signer_id,
            "signature.reject",
            "document",
            document_id,
            correlation_id,
            {"reason": reason},
        )
        return rejected

    # --------------------------------------------------------
    # Document Queries
    # --------------------------------------------------------

    def list_documents(
        self,
        actor_roles: set[str],
        region: Region | None = None,
        document_type: DocumentType | None = None,
    ) -> list[GeneratedDocument]:
        """List generated documents with optional filters."""
        self._require_doc_generate(actor_roles)
        docs = list(self._documents.values())
        if region:
            docs = [d for d in docs if d.region == region]
        if document_type:
            docs = [d for d in docs if d.document_type == document_type]
        return docs

    def get_document(
        self, actor_roles: set[str], document_id: UUID
    ) -> GeneratedDocument:
        """Get a specific document by ID."""
        self._require_doc_generate(actor_roles)
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        return self._documents[document_id]

    def verify_document_integrity(
        self, actor_roles: set[str], document_id: UUID, expected_hash: str
    ) -> bool:
        """Verify document integrity by comparing content hash."""
        self._require_doc_generate(actor_roles)
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        return self._documents[document_id].content_hash == expected_hash

    # --------------------------------------------------------
    # SOS Tracking (Wyoming)
    # --------------------------------------------------------

    def create_sos_reminder(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        reminder_type: str,
        due_date: date,
    ) -> SOSReminder:
        """Create a Secretary of State reminder (Wyoming)."""
        self._require_admin(actor_roles)

        config = REGIONAL_CONFIGS[Region.WYOMING_US]

        reminder = SOSReminder(
            id=uuid4(),
            region=Region.WYOMING_US,
            reminder_type=reminder_type,
            due_date=due_date,
            entity_name=config.entity_name,
            sos_file_number=config.sos_file_number or "",
        )
        self._sos_reminders[reminder.id] = reminder

        self._audit(
            actor_id,
            "sos_reminder.create",
            "sos_reminder",
            reminder.id,
            correlation_id,
            {"reminder_type": reminder_type, "due_date": str(due_date)},
        )
        return reminder

    def complete_sos_reminder(
        self,
        actor_id: str,
        actor_roles: set[str],
        correlation_id: str,
        reminder_id: UUID,
    ) -> SOSReminder:
        """Mark an SOS reminder as completed."""
        self._require_admin(actor_roles)

        if reminder_id not in self._sos_reminders:
            raise ValueError(f"Reminder {reminder_id} not found")

        old = self._sos_reminders[reminder_id]
        completed = SOSReminder(
            id=old.id,
            region=old.region,
            reminder_type=old.reminder_type,
            due_date=old.due_date,
            entity_name=old.entity_name,
            sos_file_number=old.sos_file_number,
            is_completed=True,
            completed_at=datetime.now(timezone.utc),
        )
        self._sos_reminders[reminder_id] = completed

        self._audit(
            actor_id,
            "sos_reminder.complete",
            "sos_reminder",
            reminder_id,
            correlation_id,
        )
        return completed

    def list_sos_reminders(
        self, actor_roles: set[str], include_completed: bool = False
    ) -> list[SOSReminder]:
        """List SOS reminders."""
        self._require_admin(actor_roles)
        reminders = list(self._sos_reminders.values())
        if not include_completed:
            reminders = [r for r in reminders if not r.is_completed]
        return reminders

    # --------------------------------------------------------
    # Regional Config Query
    # --------------------------------------------------------

    def get_regional_config(self, region: Region) -> RegionalConfig:
        """Get configuration for a region."""
        return REGIONAL_CONFIGS[region]

    def list_regions(self) -> list[Region]:
        """List all supported regions."""
        return list(Region)

    # --------------------------------------------------------
    # Audit Trail
    # --------------------------------------------------------

    def list_audit_events(
        self,
        actor_roles: set[str],
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """List audit events (admin/auditor only)."""
        if not actor_roles & {"admin", "auditor"}:
            raise PermissionError("Audit access required")
        events = self._audit_log[-limit:]
        if entity_type:
            events = [e for e in events if e.entity_type == entity_type]
        return events
