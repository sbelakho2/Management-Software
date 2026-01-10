"""Tests for Document Generation & Regional Compliance (Development Plan 22.11-22.12)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.document_regional import (
    DocumentRegionalService,
    Region,
    Currency,
    DocumentType,
    SignatureStatus,
    InvoiceData,
    PayslipData,
    REGIONAL_CONFIGS,
    MA_TVA_RATES,
    TN_TVA_RATES,
    WY_SALES_TAX_RATES,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> DocumentRegionalService:
    return DocumentRegionalService()


@pytest.fixture
def admin_roles() -> set[str]:
    return {"admin"}


@pytest.fixture
def finance_roles() -> set[str]:
    return {"finance"}


@pytest.fixture
def ops_roles() -> set[str]:
    return {"ops"}


@pytest.fixture
def auditor_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def viewer_roles() -> set[str]:
    return {"viewer"}


# ============================================================
# Regional Configuration Tests
# ============================================================


class TestRegionalConfiguration:
    def test_morocco_config_has_required_fields(self) -> None:
        config = REGIONAL_CONFIGS[Region.MOROCCO]
        assert config.ice is not None
        assert config.if_code is not None
        assert config.rc is not None
        assert config.cnss is not None
        assert config.currency == Currency.MAD
        assert config.logo_asset == "StarzMLogo.jpg"

    def test_tunisia_config_has_required_fields(self) -> None:
        config = REGIONAL_CONFIGS[Region.TUNISIA]
        assert config.mf is not None
        assert config.rc is not None
        assert config.cd is not None
        assert config.currency == Currency.TND
        assert config.logo_asset == "StarzLogo.png"

    def test_wyoming_config_has_required_fields(self) -> None:
        config = REGIONAL_CONFIGS[Region.WYOMING_US]
        assert config.ein is not None
        assert config.sos_file_number is not None
        assert config.currency == Currency.USD

    def test_list_regions(self, svc: DocumentRegionalService) -> None:
        regions = svc.list_regions()
        assert Region.MOROCCO in regions
        assert Region.TUNISIA in regions
        assert Region.WYOMING_US in regions


# ============================================================
# Tax Calculation Tests
# ============================================================


class TestTaxCalculations:
    def test_morocco_tva_standard(self, svc: DocumentRegionalService) -> None:
        tax, total = svc.calculate_tva_morocco(Decimal("1000"), "standard")
        assert tax == Decimal("200")
        assert total == Decimal("1200")

    def test_morocco_tva_reduced_14(self, svc: DocumentRegionalService) -> None:
        tax, total = svc.calculate_tva_morocco(Decimal("1000"), "reduced_14")
        assert tax == Decimal("140")
        assert total == Decimal("1140")

    def test_morocco_tva_exempt(self, svc: DocumentRegionalService) -> None:
        tax, total = svc.calculate_tva_morocco(Decimal("1000"), "exempt")
        assert tax == Decimal("0")
        assert total == Decimal("1000")

    def test_tunisia_tva_standard(self, svc: DocumentRegionalService) -> None:
        tax, total = svc.calculate_tva_tunisia(Decimal("1000"), "standard")
        assert tax == Decimal("190")
        assert total == Decimal("1190")

    def test_tunisia_tva_reduced_7(self, svc: DocumentRegionalService) -> None:
        tax, total = svc.calculate_tva_tunisia(Decimal("1000"), "reduced_7")
        assert tax == Decimal("70")
        assert total == Decimal("1070")

    def test_tunisia_withholding_tax(self, svc: DocumentRegionalService) -> None:
        withholding = svc.calculate_withholding_tunisia(Decimal("1000"))
        assert withholding == Decimal("150")

    def test_wyoming_sales_tax(self, svc: DocumentRegionalService) -> None:
        tax, total = svc.calculate_sales_tax_wyoming(Decimal("1000"))
        # State 4% + Laramie County 1% = 5%
        assert tax == Decimal("50")
        assert total == Decimal("1050")


# ============================================================
# Contribution Calculation Tests
# ============================================================


class TestContributionCalculations:
    def test_morocco_contributions(self, svc: DocumentRegionalService) -> None:
        gross = Decimal("10000")
        contributions = svc.calculate_contributions_morocco(gross)

        assert "cnss_short_term" in contributions
        assert "cnss_long_term" in contributions
        assert "amo" in contributions

        # AMO employer: 2.48%
        assert contributions["amo"]["employer"] == Decimal("248.00")
        # AMO employee: 2.27%
        assert contributions["amo"]["employee"] == Decimal("227.00")

    def test_tunisia_contributions(self, svc: DocumentRegionalService) -> None:
        gross = Decimal("5000")
        contributions = svc.calculate_contributions_tunisia(gross)

        assert "cnss" in contributions
        assert "tfp" in contributions
        assert "foprolos" in contributions

    def test_wyoming_contributions(self, svc: DocumentRegionalService) -> None:
        gross = Decimal("5000")
        contributions = svc.calculate_contributions_wyoming(gross)

        assert "workers_comp" in contributions
        assert "unemployment" in contributions

        # Workers' comp: 1.5%
        assert contributions["workers_comp"]["employer"] == Decimal("75.00")


# ============================================================
# Leave Accrual Tests
# ============================================================


class TestLeaveAccrual:
    def test_morocco_leave_accrual(self, svc: DocumentRegionalService) -> None:
        # 1.5 days/month
        balance = svc.calculate_leave_accrual_morocco(12)
        assert balance == Decimal("18")

    def test_tunisia_leave_accrual(self, svc: DocumentRegionalService) -> None:
        balance = svc.calculate_leave_accrual_tunisia(12)
        assert balance == Decimal("18")

    def test_wyoming_leave_accrual(self, svc: DocumentRegionalService) -> None:
        # 1.25 days/month
        balance = svc.calculate_leave_accrual_wyoming(12)
        assert balance == Decimal("15")


# ============================================================
# Logo Asset Registry Tests
# ============================================================


class TestLogoAssetRegistry:
    def test_register_logo_asset(
        self, svc: DocumentRegionalService, admin_roles: set[str]
    ) -> None:
        asset = svc.register_logo_asset(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            filename="StarzMLogo.jpg",
            content=b"fake image content",
            width_px=200,
            height_px=100,
            format="jpeg",
        )

        assert asset.filename == "StarzMLogo.jpg"
        assert asset.is_optimized is False

    def test_optimize_logo_asset(
        self, svc: DocumentRegionalService, admin_roles: set[str]
    ) -> None:
        asset = svc.register_logo_asset(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            filename="StarzLogo.png",
            content=b"fake image",
            width_px=150,
            height_px=75,
            format="png",
        )

        optimized = svc.optimize_logo_asset(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            asset_id=asset.id,
        )

        assert optimized.is_optimized is True

    def test_non_admin_cannot_register_logo(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Admin role required"):
            svc.register_logo_asset(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id="cor-1",
                filename="test.png",
                content=b"test",
                width_px=100,
                height_px=50,
                format="png",
            )


# ============================================================
# Letterhead Tests
# ============================================================


class TestLetterheadTemplates:
    def test_register_letterhead(
        self, svc: DocumentRegionalService, admin_roles: set[str]
    ) -> None:
        asset = svc.register_logo_asset(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            filename="StarzMLogo.jpg",
            content=b"logo",
            width_px=200,
            height_px=100,
            format="jpeg",
        )

        letterhead = svc.register_letterhead(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            region=Region.MOROCCO,
            name="Formal Correspondence",
            logo_asset_id=asset.id,
            header_text="Starz Morocco SARL",
            footer_text="Tangier Automotive City",
        )

        assert letterhead.region == Region.MOROCCO
        assert letterhead.name == "Formal Correspondence"


# ============================================================
# Invoice Generation Tests
# ============================================================


class TestInvoiceGeneration:
    def test_generate_morocco_invoice(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-MA-2025-001",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Customer Corp",
            customer_address="123 Main St, Casablanca",
            customer_tax_id="MA123456",
            line_items=({"description": "Widget", "qty": 10, "price": 100},),
            subtotal=Decimal("1000"),
            tax_amount=Decimal("200"),
            total=Decimal("1200"),
            tax_rate_applied="20%",
        )

        doc = svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.MOROCCO,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
        )

        assert doc.document_type == DocumentType.INVOICE
        assert doc.region == Region.MOROCCO
        assert doc.content_hash is not None
        assert doc.signature_status == SignatureStatus.PENDING

    def test_generate_tunisia_invoice(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-TN-2025-001",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Tunisia Customer",
            customer_address="5 Rue X, Tunis",
            customer_tax_id="TN123456",
            line_items=({"description": "Part A", "qty": 5, "price": 200},),
            subtotal=Decimal("1000"),
            tax_amount=Decimal("190"),
            total=Decimal("1190"),
            tax_rate_applied="19%",
        )

        doc = svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.TUNISIA,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
        )

        assert doc.region == Region.TUNISIA

    def test_invoice_with_entity_binding(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        shipment_id = uuid4()
        invoice_data = InvoiceData(
            invoice_number="INV-WY-2025-001",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="US Customer",
            customer_address="100 Main St, Cheyenne, WY",
            customer_tax_id=None,
            line_items=(),
            subtotal=Decimal("500"),
            tax_amount=Decimal("25"),
            total=Decimal("525"),
            tax_rate_applied="5%",
        )

        doc = svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.WYOMING_US,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
            bound_entity_type="shipment",
            bound_entity_id=shipment_id,
        )

        assert doc.bound_entity_type == "shipment"
        assert doc.bound_entity_id == shipment_id


# ============================================================
# Payslip Generation Tests
# ============================================================


class TestPayslipGeneration:
    def test_generate_morocco_payslip(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        payslip_data = PayslipData(
            employee_id="EMP-001",
            employee_name="Ahmed Ben Ali",
            pay_period_start=date(2025, 1, 1),
            pay_period_end=date(2025, 1, 31),
            gross_salary=Decimal("15000"),
            contributions=({"name": "CNSS", "amount": Decimal("750")},),
            net_salary=Decimal("14250"),
            region=Region.MOROCCO,
        )

        doc = svc.generate_payslip(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            payslip_data=payslip_data,
            entity_version_id=uuid4(),
        )

        assert doc.document_type == DocumentType.PAYSLIP
        assert doc.region == Region.MOROCCO


# ============================================================
# COC Generation Tests
# ============================================================


class TestCOCGeneration:
    def test_generate_coc_with_binding(
        self, svc: DocumentRegionalService, ops_roles: set[str]
    ) -> None:
        lot_id = uuid4()

        doc = svc.generate_coc(
            actor_id="ops1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            region=Region.MOROCCO,
            product_description="Steel Rod 10mm",
            lot_number="LOT-2025-001",
            inspection_results={"Hardness": "PASS", "Dimensions": "PASS"},
            entity_version_id=uuid4(),
            bound_entity_id=lot_id,
        )

        assert doc.document_type == DocumentType.COC
        assert doc.bound_entity_type == "lot"
        assert doc.bound_entity_id == lot_id


# ============================================================
# Electronic Signature Tests
# ============================================================


class TestElectronicSignature:
    def test_request_and_apply_signature(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Customer",
            customer_address="Address",
            customer_tax_id=None,
            line_items=(),
            subtotal=Decimal("100"),
            tax_amount=Decimal("20"),
            total=Decimal("120"),
            tax_rate_applied="20%",
        )

        doc = svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.MOROCCO,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
        )

        # Request signature
        svc.request_signature(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            document_id=doc.id,
            signer_id="manager1",
        )

        # Apply signature
        signed = svc.apply_signature(
            signer_id="manager1",
            signer_roles={"gm"},
            correlation_id="cor-3",
            document_id=doc.id,
        )

        assert signed.signature_status == SignatureStatus.SIGNED
        assert signed.signed_by == "manager1"

    def test_reject_signature(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-002",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Customer",
            customer_address="Address",
            customer_tax_id=None,
            line_items=(),
            subtotal=Decimal("100"),
            tax_amount=Decimal("20"),
            total=Decimal("120"),
            tax_rate_applied="20%",
        )

        doc = svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.TUNISIA,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
        )

        rejected = svc.reject_signature(
            signer_id="manager1",
            signer_roles={"gm"},
            correlation_id="cor-2",
            document_id=doc.id,
            reason="Incorrect amounts",
        )

        assert rejected.signature_status == SignatureStatus.REJECTED


# ============================================================
# Document Integrity Tests
# ============================================================


class TestDocumentIntegrity:
    def test_verify_document_hash(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-003",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Customer",
            customer_address="Address",
            customer_tax_id=None,
            line_items=(),
            subtotal=Decimal("100"),
            tax_amount=Decimal("20"),
            total=Decimal("120"),
            tax_rate_applied="20%",
        )

        doc = svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.WYOMING_US,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
        )

        # Correct hash
        assert svc.verify_document_integrity(
            actor_roles=finance_roles, document_id=doc.id, expected_hash=doc.content_hash
        )

        # Wrong hash
        assert not svc.verify_document_integrity(
            actor_roles=finance_roles, document_id=doc.id, expected_hash="bad_hash"
        )


# ============================================================
# SOS Reminder Tests (Wyoming)
# ============================================================


class TestSOSReminders:
    def test_create_sos_reminder(
        self, svc: DocumentRegionalService, admin_roles: set[str]
    ) -> None:
        reminder = svc.create_sos_reminder(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            reminder_type="annual_report",
            due_date=date(2025, 3, 1),
        )

        assert reminder.reminder_type == "annual_report"
        assert reminder.is_completed is False

    def test_complete_sos_reminder(
        self, svc: DocumentRegionalService, admin_roles: set[str]
    ) -> None:
        reminder = svc.create_sos_reminder(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            reminder_type="registered_agent",
            due_date=date(2025, 6, 1),
        )

        completed = svc.complete_sos_reminder(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            reminder_id=reminder.id,
        )

        assert completed.is_completed is True
        assert completed.completed_at is not None

    def test_list_sos_reminders_excludes_completed(
        self, svc: DocumentRegionalService, admin_roles: set[str]
    ) -> None:
        r1 = svc.create_sos_reminder(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            reminder_type="annual_report",
            due_date=date(2025, 3, 1),
        )
        svc.create_sos_reminder(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            reminder_type="registered_agent",
            due_date=date(2025, 6, 1),
        )

        svc.complete_sos_reminder(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-3",
            reminder_id=r1.id,
        )

        pending = svc.list_sos_reminders(actor_roles=admin_roles)
        assert len(pending) == 1

        all_reminders = svc.list_sos_reminders(
            actor_roles=admin_roles, include_completed=True
        )
        assert len(all_reminders) == 2


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_viewer_cannot_generate_documents(
        self, svc: DocumentRegionalService, viewer_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Customer",
            customer_address="Address",
            customer_tax_id=None,
            line_items=(),
            subtotal=Decimal("100"),
            tax_amount=Decimal("20"),
            total=Decimal("120"),
            tax_rate_applied="20%",
        )

        with pytest.raises(PermissionError, match="Document generation access required"):
            svc.generate_invoice(
                actor_id="viewer1",
                actor_roles=viewer_roles,
                correlation_id="cor-1",
                region=Region.MOROCCO,
                invoice_data=invoice_data,
                entity_version_id=uuid4(),
            )


# ============================================================
# Audit Trail Tests
# ============================================================


class TestAuditTrail:
    def test_audit_trail_for_document_operations(
        self, svc: DocumentRegionalService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        invoice_data = InvoiceData(
            invoice_number="INV-AUDIT-001",
            invoice_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            customer_name="Customer",
            customer_address="Address",
            customer_tax_id=None,
            line_items=(),
            subtotal=Decimal("100"),
            tax_amount=Decimal("20"),
            total=Decimal("120"),
            tax_rate_applied="20%",
        )

        svc.generate_invoice(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            region=Region.MOROCCO,
            invoice_data=invoice_data,
            entity_version_id=uuid4(),
        )

        events = svc.list_audit_events(actor_roles=admin_roles)
        assert any(e.action == "document.generate" for e in events)

    def test_non_auditor_cannot_view_audit(
        self, svc: DocumentRegionalService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Audit access required"):
            svc.list_audit_events(actor_roles=finance_roles)
