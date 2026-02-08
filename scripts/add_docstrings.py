#!/usr/bin/env python3
"""Add module-level docstrings to Python files that are missing them.

Checklist item: #499
"""
import os

DOCSTRINGS = {
    "backend/src/sensei/services/core/escalation_policy.py": '"""\nEscalation Policy Engine.\n\nDefines time-based escalation rules for open items (NCRs, CAPAs,\nwork orders, approvals). Automatically escalates overdue items\nthrough configurable escalation chains with notification triggers.\n"""\n',

    "backend/src/sensei/services/core/missing_info_workflow.py": '"""\nMissing Information Workflow.\n\nManages the lifecycle of missing-information requests during\nRFQ processing. Tracks requests, sends reminders, and processes\nresponses with template-based email generation.\n"""\n',

    "backend/src/sensei/services/production/lot_serial_traceability.py": '"""\nLot & Serial Traceability Service.\n\nFull forward/backward traceability for lots and serial numbers.\nSupports genealogy tracking, certificate management, recall\nprocessing, and regulatory compliance (FDA 21 CFR Part 11).\n"""\n',

    "backend/src/sensei/services/production/label_printing.py": '"""\nLabel Printing Service.\n\nManages label templates, print job queuing, and barcode/QR code\ngeneration for production, shipping, and inventory labels.\nSupports ZPL, EPL, and PDF label formats.\n"""\n',

    "backend/src/sensei/services/production/spc_scrap_rework.py": '"""\nSPC, Scrap & Rework Service.\n\nStatistical Process Control (SPC) charting, scrap/rework tracking,\nCost of Poor Quality (COPQ) analysis, and ERP sync queue\nfor quality-related transactions.\n"""\n',

    "backend/src/sensei/services/finance/ledger_router.py": '"""\nAccounting Ledger Router.\n\nRoutes accounting operations to either the in-memory or\npersistent (database-backed) ledger service based on\nconfiguration. Provides a unified API surface.\n"""\n',

    "backend/src/sensei/services/finance/accounts_payable.py": '"""\nAccounts Payable Service.\n\nManages purchase requisitions, purchase orders, vendor invoices,\npayment runs, goods receipts, and three-way matching.\nSupports approval workflows and payment scheduling.\n"""\n',

    "backend/src/sensei/services/finance/accounts_receivable.py": '"""\nAccounts Receivable Service.\n\nManages customer invoicing, payment collection, credit memos,\naging analysis, and dunning workflows. Tracks customer\nbalances and payment history.\n"""\n',

    "backend/src/sensei/services/finance/cost_accounting.py": '"""\nCost Accounting Service.\n\nManages cost centers, cost allocations, overhead rate\ncalculations, and activity-based costing. Supports\nstandard costing and variance analysis.\n"""\n',

    "backend/src/sensei/services/finance/tax_service.py": '"""\nTax Service.\n\nManages tax rates, tax rules, jurisdiction mappings, and\ntax calculations for sales tax, VAT, and withholding tax.\nSupports multi-jurisdiction tax compliance.\n"""\n',

    "backend/src/sensei/services/ai/knowledge_ingestion.py": '"""\nKnowledge Ingestion Service.\n\nIngests documents (PDF, DOCX, TXT, Markdown) into the\nknowledge base. Performs semantic chunking, metadata\nextraction, and vector embedding for retrieval.\n"""\n',
}

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

count = 0
for rel_path, docstring in DOCSTRINGS.items():
    full_path = os.path.join(BASE, rel_path)
    if not os.path.exists(full_path):
        print(f"  SKIP (not found): {rel_path}")
        continue

    with open(full_path, "r") as f:
        content = f.read()

    # Check if already has a docstring
    stripped = content.lstrip()
    if stripped.startswith('"""') or stripped.startswith("'''"):
        print(f"  SKIP (has docstring): {rel_path}")
        continue

    # Handle __future__ import - docstring goes before it
    if content.startswith("from __future__"):
        new_content = docstring + content
    else:
        new_content = docstring + content

    with open(full_path, "w") as f:
        f.write(new_content)

    count += 1
    print(f"  Added docstring: {rel_path}")

print(f"\nTotal: {count} docstrings added")
