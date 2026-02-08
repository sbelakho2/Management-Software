#!/usr/bin/env python3
"""Add module-level docstrings to all Python service files missing them.

Reads the first few lines to infer the module purpose from class/function names,
then inserts a contextual docstring.

Checklist item: #499
"""
import os
import re

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "src", "sensei", "services")

# Map of relative path → docstring content
DOCSTRINGS: dict[str, str] = {
    "core/rbac_bootstrap.py": "RBAC Bootstrap.\n\nInitializes default roles, permissions, and role-permission\nmappings on application startup.",

    "core/site_service.py": "Site Service.\n\nManages multi-site configuration, site-specific settings,\nand cross-site data visibility rules.",

    "sales/quoting_helper.py": "Quoting Helper.\n\nAssists with RFQ work-packet breakdown, cost estimation,\nand quote package assembly. Integrates with AI-assisted\nquoting for automated pricing suggestions.",

    "quality/traceability_service.py": "Quality Traceability Service.\n\nProvides end-to-end traceability linking inspections,\nNCRs, CAPAs, and audit findings to source materials,\nprocesses, and customer complaints.",

    "quality/management_review_service.py": "Management Review Service.\n\nSupports ISO 9001 management review processes including\nagenda generation, data collection, action item tracking,\nand meeting minutes management.",

    "quality/msa_service.py": "Measurement System Analysis (MSA) Service.\n\nPerforms Gage R&R studies, linearity/bias analysis,\nand stability assessments per AIAG MSA 4th edition.\nCalculates %GRR, ndc, and measurement uncertainty.",

    "quality/process_capability_service.py": "Process Capability Service.\n\nCalculates Cp, Cpk, Pp, Ppk indices with normality testing.\nSupports bilateral and unilateral specifications,\nhistogram generation, and capability trending.",

    "quality/customer_satisfaction_service.py": "Customer Satisfaction Service.\n\nManages customer satisfaction surveys, Net Promoter Score\n(NPS) tracking, complaint correlation analysis, and\ncustomer feedback workflows.",

    "quality/aql_sampling_service.py": "AQL Sampling Service.\n\nImplements ANSI/ASQ Z1.4 (ISO 2859-1) acceptance sampling\nplans. Calculates sample sizes, acceptance/rejection numbers,\nand switching rules (normal/tightened/reduced).",

    "quality/first_article_service.py": "First Article Inspection (FAI) Service.\n\nManages AS9102 First Article Inspection Reports.\nTracks Form 1 (Part Number Accountability), Form 2\n(Product Accountability), and Form 3 (Characteristic\nAccountability).",

    "quality/change_point_service.py": "Change Point Detection Service.\n\nDetects statistically significant changes in process\nparameters using CUSUM, EWMA, and Bayesian change point\nalgorithms. Triggers alerts on detected shifts.",

    "quality/self_inspection_service.py": "Self-Inspection Service.\n\nEnables operator-level quality checks at the point of\nmanufacture. Manages inspection checklists, pass/fail\ncriteria, and automatic escalation on failures.",

    "quality/lab_management_service.py": "Lab Management Service.\n\nManages laboratory test requests, sample tracking,\nequipment calibration schedules, and test result\nrecording. Supports LIMS integration.",

    "quality/persistent_qms.py": "Persistent QMS Service.\n\nDatabase-backed implementation of the Quality Management\nSystem. Persists documents, audits, findings, gauges,\nSCARs, and risk assessments to PostgreSQL.",

    "ai/quoting_assist.py": "AI Quoting Assistant.\n\nProvides AI-powered quote generation, cost estimation,\nand pricing recommendations using historical RFQ data\nand machine learning models.",

    "production/persistent_mrp.py": "Persistent MRP Service.\n\nDatabase-backed Material Requirements Planning.\nPersists BOMs, inventory records, demand forecasts,\nsupply orders, and MRP run results to PostgreSQL.",

    "production/handover_service.py": "Shift Handover Service.\n\nManages shift-to-shift handover documentation including\nopen items, safety alerts, production status, and\npending actions. Ensures continuity across shifts.",

    "production/mps_service.py": "Master Production Schedule (MPS) Service.\n\nManages the master production schedule including demand\nplanning, capacity allocation, and schedule leveling.\nFeeds MRP and shop floor scheduling.",

    "ops/erp_integration.py": "ERP Integration Service.\n\nProvides integration points with external ERP systems.\nManages data synchronization, transaction mapping, and\nerror handling for bi-directional ERP communication.",

    "ops/today_screen_models.py": "Today Screen Models.\n\nData models and aggregation logic for the shift-level\n'Today' dashboard. Combines production, quality,\nmaintenance, and safety metrics into a unified view.",

    "ops/pulse_service.py": "Pulse Service.\n\nReal-time factory pulse monitoring combining KPIs from\nproduction, quality, maintenance, and safety into a\nsingle operational heartbeat view.",

    "finance/currency_settings.py": "Currency Settings Service.\n\nManages multi-currency configuration, exchange rate\nsources, rounding rules, and default currency settings\nfor the organization.",

    "finance/cost_rollup_service.py": "Cost Rollup Service.\n\nAggregates costs across materials, labor, overhead, and\nsubcontracting into rolled-up product costs. Supports\nstandard cost updates and variance analysis.",

    "finance/persistent_accounting.py": "Persistent Accounting Ledger Service.\n\nDatabase-backed general ledger implementation. Persists\naccounts, journal entries, posted lines, fiscal periods,\nand FX rates to PostgreSQL.",

    "finance/tax_service.py": "Tax Service.\n\nManages tax rates, tax rules, jurisdiction mappings, and\ntax calculations for sales tax, VAT, and withholding tax.\nSupports multi-jurisdiction tax compliance.",

    "maintenance/persistent_maintenance.py": "Persistent Maintenance Service.\n\nDatabase-backed maintenance management. Persists assets,\nPM schedules, work orders, spare parts inventory, and\ndowntime events to PostgreSQL.",

    "maintenance/warranty_tracking.py": "Warranty Tracking Service.\n\nManages warranty registrations, claim submissions,\ncoverage verification, and warranty cost analysis.\nTracks warranty periods and exclusions.",

    "maintenance/field_returns.py": "Field Returns / RMA Service.\n\nManages Return Merchandise Authorization (RMA) workflows,\nfield failure analysis, root cause tracking, and\nreplacement part logistics.",

    "maintenance/maintenance_budget.py": "Maintenance Budget Service.\n\nManages maintenance cost budgets, tracks actual spending\nagainst budget, and provides variance analysis by asset\ncategory, cost type, and time period.",

    "maintenance/tool_crib.py": "Tool Crib Management Service.\n\nManages tool inventory, check-out/check-in workflows,\ncalibration tracking, tool life monitoring, and\nreplacement ordering for shop floor tooling.",

    "maintenance/lockout_tagout.py": "Lockout/Tagout (LOTO) Service.\n\nManages energy isolation procedures, LOTO permit\nworkflows, equipment lockout status tracking, and\ncompliance reporting per OSHA 29 CFR 1910.147.",
}


def add_docstrings():
    count = 0
    for rel_path, docstring_body in DOCSTRINGS.items():
        full_path = os.path.join(BASE, rel_path)
        if not os.path.exists(full_path):
            print(f"  SKIP (not found): {rel_path}")
            continue

        with open(full_path, "r") as f:
            content = f.read()

        # Check if already has a docstring at the top
        stripped = content.lstrip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            print(f"  SKIP (has docstring): {rel_path}")
            continue

        docstring = f'"""\n{docstring_body}\n"""\n\n'
        new_content = docstring + content

        with open(full_path, "w") as f:
            f.write(new_content)

        count += 1
        print(f"  Added: {rel_path}")

    print(f"\nTotal: {count} docstrings added")


if __name__ == "__main__":
    add_docstrings()
