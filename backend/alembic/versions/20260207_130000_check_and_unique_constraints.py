"""Add check constraints and unique constraints

Adds:
- Check constraint on opportunities.probability (0-100) (#170/#402)
- Check constraint on quotes.discount_percentage (0-100) (#170/#402)
- Check constraint on quote_line_items.discount_percentage (0-100) (#170/#402)
- Check constraint on quotes.tax_rate (0-100) (#170/#402)
- Unique constraint on hr_job_applications(job_opening_id, email) (#176/#401)

Revision ID: 20260207_130000
Revises: 20260207_120000
Create Date: 2026-02-07
"""
from alembic import op


# revision identifiers
revision = "20260207_130000"
down_revision = "20260207_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add check constraints and unique constraints."""

    # ── Check constraints on percentage/probability columns (#170, #402) ──

    # opportunities.probability must be 0–100
    op.create_check_constraint(
        "ck_opportunities_probability_range",
        "opportunities",
        "probability >= 0 AND probability <= 100",
    )

    # quotes.discount_percentage must be 0–100 (nullable, only check when set)
    op.create_check_constraint(
        "ck_quotes_discount_pct_range",
        "quotes",
        "discount_percentage IS NULL OR (discount_percentage >= 0 AND discount_percentage <= 100)",
    )

    # quotes.tax_rate must be 0–100 (nullable, only check when set)
    op.create_check_constraint(
        "ck_quotes_tax_rate_range",
        "quotes",
        "tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100)",
    )

    # quote_line_items.discount_percentage must be 0–100 (nullable)
    op.create_check_constraint(
        "ck_quote_line_items_discount_pct_range",
        "quote_line_items",
        "discount_percentage IS NULL OR (discount_percentage >= 0 AND discount_percentage <= 100)",
    )

    # ── Unique constraint on job applications (#176, #401) ──
    # Prevent duplicate applications from same email to same job opening
    op.create_unique_constraint(
        "uq_hr_job_applications_opening_email",
        "hr_job_applications",
        ["job_opening_id", "email"],
    )


def downgrade() -> None:
    """Remove check constraints and unique constraints."""
    op.drop_constraint("uq_hr_job_applications_opening_email", "hr_job_applications", type_="unique")
    op.drop_constraint("ck_quote_line_items_discount_pct_range", "quote_line_items", type_="check")
    op.drop_constraint("ck_quotes_tax_rate_range", "quotes", type_="check")
    op.drop_constraint("ck_quotes_discount_pct_range", "quotes", type_="check")
    op.drop_constraint("ck_opportunities_probability_range", "opportunities", type_="check")
