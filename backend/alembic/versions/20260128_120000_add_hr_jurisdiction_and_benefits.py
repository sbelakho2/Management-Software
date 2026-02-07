"""Add HR jurisdiction column and North Africa benefits tables.

Revision ID: add_hr_jurisdiction
Revises: 20260126_150000_service_persistence
Create Date: 2026-01-28 12:00:00.000000

This migration:
1. Adds 'jurisdiction' column to hr_employees (default='TN' for Tunisia)
2. Creates tables for North Africa social security administration:
   - hr_jurisdiction_configs (statutory rates by country)
   - hr_social_security_records (employee SS registration)
   - hr_contribution_periods (monthly/quarterly contributions)
   - hr_family_allowances (family benefit claims)
   - hr_sickness_maternity_benefits
   - hr_pension_entitlements
   - hr_work_injury_records
   - hr_unemployment_benefits
   - hr_death_survivor_benefits
   - hr_medical_coverage

Legacy Note: All existing employees default to Tunisia (TN) jurisdiction
as they were hired under Tunisian CNSS regulations.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = "add_hr_jurisdiction"
down_revision = "20260126_150000_service_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # Step 1: Add jurisdiction column to existing hr_employees table
    # Default to "TN" (Tunisia) for all legacy employees
    # =========================================================================
    op.add_column(
        "hr_employees",
        sa.Column(
            "jurisdiction",
            sa.String(length=10),
            nullable=False,
            server_default="TN",
        ),
    )
    # Create index for jurisdiction-based queries
    op.create_index(
        "ix_hr_employees_jurisdiction",
        "hr_employees",
        ["jurisdiction"],
    )

    # =========================================================================
    # Step 2: Create hr_jurisdiction_configs table
    # Stores statutory rates and limits for each supported country
    # =========================================================================
    op.create_table(
        "hr_jurisdiction_configs",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("country_name", sa.String(length=100), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("ss_agency_name", sa.String(length=255), nullable=False),
        sa.Column("ss_agency_code", sa.String(length=50), nullable=True),
        # Employee contribution rates
        sa.Column("employee_pension_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("employee_health_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("employee_unemployment_rate", sa.Numeric(6, 4), server_default="0", nullable=False),
        sa.Column("employee_family_rate", sa.Numeric(6, 4), server_default="0", nullable=False),
        # Employer contribution rates
        sa.Column("employer_pension_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("employer_health_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("employer_work_injury_rate_min", sa.Numeric(6, 4), server_default="0", nullable=False),
        sa.Column("employer_work_injury_rate_max", sa.Numeric(6, 4), server_default="0", nullable=False),
        sa.Column("employer_family_rate", sa.Numeric(6, 4), server_default="0", nullable=False),
        sa.Column("employer_unemployment_rate", sa.Numeric(6, 4), server_default="0", nullable=False),
        # Caps
        sa.Column("min_monthly_earnings", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_monthly_earnings", sa.Numeric(12, 2), nullable=True),
        # Leave entitlements
        sa.Column("annual_leave_days", sa.Integer(), server_default="21", nullable=False),
        sa.Column("maternity_leave_days", sa.Integer(), nullable=False),
        sa.Column("paternity_leave_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sick_leave_max_days", sa.Integer(), nullable=False),
        sa.Column("maternity_benefit_rate", sa.Numeric(5, 2), nullable=False),
        # Retirement
        sa.Column("retirement_age_male", sa.Integer(), server_default="60", nullable=False),
        sa.Column("retirement_age_female", sa.Integer(), server_default="60", nullable=False),
        sa.Column("min_contribution_years", sa.Integer(), server_default="10", nullable=False),
        sa.Column("pension_accrual_rate", sa.Numeric(5, 3), server_default="0.020", nullable=False),
        # Metadata
        sa.Column("extra_rules", JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jurisdiction", name="uq_hr_jurisdiction_configs_jurisdiction"),
    )

    # =========================================================================
    # Step 3: Create hr_social_security_records table
    # Employee registration with social security agency
    # =========================================================================
    op.create_table(
        "hr_social_security_records",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("ss_number", sa.String(length=50), nullable=False),
        sa.Column("registration_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("employer_ss_number", sa.String(length=50), nullable=True),
        sa.Column("affiliation_number", sa.String(length=50), nullable=True),
        sa.Column("sector_code", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jurisdiction", "ss_number", name="uq_ss_number_per_jurisdiction"),
    )
    op.create_index("ix_hr_social_security_records_employee_id", "hr_social_security_records", ["employee_id"])

    # =========================================================================
    # Step 4: Create hr_contribution_periods table
    # Monthly/quarterly contribution records
    # =========================================================================
    op.create_table(
        "hr_contribution_periods",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("employee_contribution", sa.Numeric(12, 2), nullable=False),
        sa.Column("employer_contribution", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_contribution", sa.Numeric(12, 2), nullable=False),
        sa.Column("pension_portion", sa.Numeric(12, 2), nullable=True),
        sa.Column("health_portion", sa.Numeric(12, 2), nullable=True),
        sa.Column("family_portion", sa.Numeric(12, 2), nullable=True),
        sa.Column("work_injury_portion", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "period_start", "period_end", name="uq_contribution_period_per_employee"),
    )
    op.create_index("ix_hr_contribution_periods_employee_id", "hr_contribution_periods", ["employee_id"])

    # =========================================================================
    # Step 5: Create hr_family_allowances table
    # =========================================================================
    op.create_table(
        "hr_family_allowances",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("child_name", sa.String(length=200), nullable=False),
        sa.Column("child_birth_date", sa.Date(), nullable=False),
        sa.Column("relationship", sa.String(length=50), server_default="child", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("monthly_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("documentation_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_family_allowances_employee_id", "hr_family_allowances", ["employee_id"])

    # =========================================================================
    # Step 6: Create hr_sickness_maternity_benefits table
    # =========================================================================
    op.create_table(
        "hr_sickness_maternity_benefits",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("benefit_type", sa.String(length=20), nullable=False),  # sickness, maternity, paternity
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("days_claimed", sa.Integer(), nullable=False),
        sa.Column("medical_certificate_ref", sa.String(length=100), nullable=True),
        sa.Column("waiting_period_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("daily_benefit_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_benefit_paid", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_sickness_maternity_benefits_employee_id", "hr_sickness_maternity_benefits", ["employee_id"])

    # =========================================================================
    # Step 7: Create hr_pension_entitlements table
    # =========================================================================
    op.create_table(
        "hr_pension_entitlements",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("calculation_date", sa.Date(), nullable=False),
        sa.Column("total_contribution_years", sa.Numeric(5, 2), nullable=False),
        sa.Column("total_contribution_months", sa.Integer(), nullable=False),
        sa.Column("average_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("projected_pension_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("eligible_retirement_date", sa.Date(), nullable=True),
        sa.Column("early_retirement_possible", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("early_retirement_reduction_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="projected", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_pension_entitlements_employee_id", "hr_pension_entitlements", ["employee_id"])

    # =========================================================================
    # Step 8: Create hr_work_injury_records table
    # =========================================================================
    op.create_table(
        "hr_work_injury_records",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("reported_date", sa.Date(), nullable=False),
        sa.Column("incident_description", sa.Text(), nullable=False),
        sa.Column("injury_type", sa.String(length=100), nullable=True),
        sa.Column("body_part_affected", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),  # minor, moderate, severe, fatal
        sa.Column("days_lost", sa.Integer(), server_default="0", nullable=False),
        sa.Column("temporary_disability_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("permanent_disability_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("benefit_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("claim_reference", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="reported", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_work_injury_records_employee_id", "hr_work_injury_records", ["employee_id"])

    # =========================================================================
    # Step 9: Create hr_unemployment_benefits table
    # =========================================================================
    op.create_table(
        "hr_unemployment_benefits",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("termination_date", sa.Date(), nullable=False),
        sa.Column("termination_reason", sa.String(length=100), nullable=False),
        sa.Column("involuntary", sa.Boolean(), nullable=False),
        sa.Column("contribution_months", sa.Integer(), nullable=False),
        sa.Column("last_salary", sa.Numeric(12, 2), nullable=False),
        sa.Column("benefit_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("monthly_benefit", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_benefit_months", sa.Integer(), nullable=True),
        sa.Column("benefit_start_date", sa.Date(), nullable=True),
        sa.Column("benefit_end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_unemployment_benefits_employee_id", "hr_unemployment_benefits", ["employee_id"])

    # =========================================================================
    # Step 10: Create hr_death_survivor_benefits table
    # =========================================================================
    op.create_table(
        "hr_death_survivor_benefits",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("death_date", sa.Date(), nullable=False),
        sa.Column("cause", sa.String(length=50), nullable=False),  # natural, work_related, accident
        sa.Column("beneficiary_name", sa.String(length=200), nullable=False),
        sa.Column("beneficiary_relationship", sa.String(length=50), nullable=False),
        sa.Column("beneficiary_id_number", sa.String(length=50), nullable=True),
        sa.Column("benefit_type", sa.String(length=50), nullable=False),  # lump_sum, survivor_pension, funeral
        sa.Column("benefit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("benefit_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("payment_frequency", sa.String(length=20), nullable=True),  # one_time, monthly
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_death_survivor_benefits_employee_id", "hr_death_survivor_benefits", ["employee_id"])

    # =========================================================================
    # Step 11: Create hr_medical_coverage table
    # =========================================================================
    op.create_table(
        "hr_medical_coverage",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("employee_id", UUID(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False),
        sa.Column("coverage_type", sa.String(length=50), nullable=False),  # inpatient, outpatient, maternity, etc
        sa.Column("provider_name", sa.String(length=255), nullable=True),
        sa.Column("provider_code", sa.String(length=50), nullable=True),
        sa.Column("card_number", sa.String(length=50), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("coverage_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("annual_limit", sa.Numeric(12, 2), nullable=True),
        sa.Column("used_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", UUID(), nullable=True),
        sa.Column("updated_by_id", UUID(), nullable=True),
        sa.Column("owner_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_medical_coverage_employee_id", "hr_medical_coverage", ["employee_id"])

    # =========================================================================
    # Step 12: Seed jurisdiction configurations with statutory rates
    # =========================================================================
    # Tunisia (CNSS)
    op.execute("""
        INSERT INTO hr_jurisdiction_configs (
            id, jurisdiction, country_name, currency_code,
            ss_agency_name, ss_agency_code,
            employee_pension_rate, employee_health_rate, employee_unemployment_rate, employee_family_rate,
            employer_pension_rate, employer_health_rate, employer_work_injury_rate_min, employer_work_injury_rate_max,
            employer_family_rate, employer_unemployment_rate,
            min_monthly_earnings, max_monthly_earnings,
            annual_leave_days, maternity_leave_days, paternity_leave_days, sick_leave_max_days,
            maternity_benefit_rate, retirement_age_male, retirement_age_female,
            min_contribution_years, pension_accrual_rate, extra_rules
        ) VALUES (
            gen_random_uuid(), 'TN', 'Tunisia', 'TND',
            'Caisse Nationale de Sécurité Sociale', 'CNSS',
            0.0486, 0.0218, 0.0, 0.0,
            0.0849, 0.0416, 0.005, 0.05,
            0.0, 0.0,
            NULL, 3276.00,
            21, 30, 2, 180,
            66.67, 60, 60,
            10, 0.020,
            '{"waiting_period_sickness_days": 5, "sickness_benefit_rate": 0.6667}'
        )
    """)

    # Morocco (CNSS)
    op.execute("""
        INSERT INTO hr_jurisdiction_configs (
            id, jurisdiction, country_name, currency_code,
            ss_agency_name, ss_agency_code,
            employee_pension_rate, employee_health_rate, employee_unemployment_rate, employee_family_rate,
            employer_pension_rate, employer_health_rate, employer_work_injury_rate_min, employer_work_injury_rate_max,
            employer_family_rate, employer_unemployment_rate,
            min_monthly_earnings, max_monthly_earnings,
            annual_leave_days, maternity_leave_days, paternity_leave_days, sick_leave_max_days,
            maternity_benefit_rate, retirement_age_male, retirement_age_female,
            min_contribution_years, pension_accrual_rate, extra_rules
        ) VALUES (
            gen_random_uuid(), 'MA', 'Morocco', 'MAD',
            'Caisse Nationale de Sécurité Sociale', 'CNSS',
            0.0489, 0.0226, 0.0019, 0.0,
            0.0898, 0.0452, 0.0042, 0.07,
            0.0665, 0.0038,
            NULL, 6000.00,
            18, 98, 3, 180,
            100.00, 60, 60,
            10, 0.020,
            '{"waiting_period_sickness_days": 3, "sickness_benefit_rate": 0.6667, "family_allowance_per_child": 200}'
        )
    """)

    # Egypt (NOSI)
    op.execute("""
        INSERT INTO hr_jurisdiction_configs (
            id, jurisdiction, country_name, currency_code,
            ss_agency_name, ss_agency_code,
            employee_pension_rate, employee_health_rate, employee_unemployment_rate, employee_family_rate,
            employer_pension_rate, employer_health_rate, employer_work_injury_rate_min, employer_work_injury_rate_max,
            employer_family_rate, employer_unemployment_rate,
            min_monthly_earnings, max_monthly_earnings,
            annual_leave_days, maternity_leave_days, paternity_leave_days, sick_leave_max_days,
            maternity_benefit_rate, retirement_age_male, retirement_age_female,
            min_contribution_years, pension_accrual_rate, extra_rules
        ) VALUES (
            gen_random_uuid(), 'EG', 'Egypt', 'EGP',
            'National Organization for Social Insurance', 'NOSI',
            0.1100, 0.01, 0.0, 0.0,
            0.1875, 0.04, 0.01, 0.03,
            0.0, 0.02,
            NULL, 12600.00,
            21, 90, 0, 180,
            75.00, 60, 60,
            10, 0.020,
            '{"waiting_period_sickness_days": 3, "sickness_benefit_rate": 0.75}'
        )
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_hr_medical_coverage_employee_id", table_name="hr_medical_coverage")
    op.drop_table("hr_medical_coverage")

    op.drop_index("ix_hr_death_survivor_benefits_employee_id", table_name="hr_death_survivor_benefits")
    op.drop_table("hr_death_survivor_benefits")

    op.drop_index("ix_hr_unemployment_benefits_employee_id", table_name="hr_unemployment_benefits")
    op.drop_table("hr_unemployment_benefits")

    op.drop_index("ix_hr_work_injury_records_employee_id", table_name="hr_work_injury_records")
    op.drop_table("hr_work_injury_records")

    op.drop_index("ix_hr_pension_entitlements_employee_id", table_name="hr_pension_entitlements")
    op.drop_table("hr_pension_entitlements")

    op.drop_index("ix_hr_sickness_maternity_benefits_employee_id", table_name="hr_sickness_maternity_benefits")
    op.drop_table("hr_sickness_maternity_benefits")

    op.drop_index("ix_hr_family_allowances_employee_id", table_name="hr_family_allowances")
    op.drop_table("hr_family_allowances")

    op.drop_index("ix_hr_contribution_periods_employee_id", table_name="hr_contribution_periods")
    op.drop_table("hr_contribution_periods")

    op.drop_index("ix_hr_social_security_records_employee_id", table_name="hr_social_security_records")
    op.drop_table("hr_social_security_records")

    op.drop_table("hr_jurisdiction_configs")

    # Remove jurisdiction column from hr_employees
    op.drop_index("ix_hr_employees_jurisdiction", table_name="hr_employees")
    op.drop_column("hr_employees", "jurisdiction")
