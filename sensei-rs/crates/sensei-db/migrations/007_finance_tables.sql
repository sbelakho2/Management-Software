-- Financial management tables for Sensei ERP
--
-- This migration adds financial tables extending the base finance tables
-- (invoices, payments, budgets, journal_entries, cost_rollups) from
-- 002_domain_tables. New tables cover the general ledger, accounting periods,
-- journal lines, purchase/sales order line items, customer/supplier invoices,
-- FX rates, tax jurisdictions, and budget allocations.

-- ── GL Accounts ───────────────────────────────────────────────────────────
-- General Ledger account chart of accounts.
CREATE TABLE IF NOT EXISTS gl_accounts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    account_number      VARCHAR(50) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    account_type        VARCHAR(30) NOT NULL DEFAULT 'expense'
                        CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    balance             DOUBLE PRECISION NOT NULL DEFAULT 0,
    parent_id           UUID REFERENCES gl_accounts(id) ON DELETE SET NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, account_number)
);

CREATE INDEX idx_gl_accounts_tenant ON gl_accounts(tenant_id);
CREATE INDEX idx_gl_accounts_type ON gl_accounts(tenant_id, account_type);
CREATE INDEX idx_gl_accounts_parent ON gl_accounts(parent_id);
CREATE INDEX idx_gl_accounts_active ON gl_accounts(tenant_id, is_active) WHERE is_active = TRUE;

-- ── Accounting Periods ────────────────────────────────────────────────────
-- Fiscal calendar periods for financial reporting.
CREATE TABLE IF NOT EXISTS accounting_periods (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'closed', 'locked')),
    fiscal_year         INT NOT NULL,
    period_number       INT NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_accounting_periods_tenant ON accounting_periods(tenant_id);
CREATE INDEX idx_accounting_periods_dates ON accounting_periods(tenant_id, start_date, end_date);
CREATE INDEX idx_accounting_periods_fiscal_year ON accounting_periods(tenant_id, fiscal_year);
CREATE INDEX idx_accounting_periods_status ON accounting_periods(tenant_id, status);

-- ── Journal Lines ─────────────────────────────────────────────────────────
-- Individual debit/credit lines within journal entries.
CREATE TABLE IF NOT EXISTS journal_lines (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entry_id            UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    account_id          UUID NOT NULL REFERENCES gl_accounts(id) ON DELETE CASCADE,
    debit               DOUBLE PRECISION NOT NULL DEFAULT 0,
    credit              DOUBLE PRECISION NOT NULL DEFAULT 0,
    description         TEXT,
    entity_type         VARCHAR(50),
    entity_id           UUID,
    cost_center         VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(entry_id, line_number)
);

CREATE INDEX idx_journal_lines_entry ON journal_lines(entry_id);
CREATE INDEX idx_journal_lines_account ON journal_lines(account_id);
CREATE INDEX idx_journal_lines_tenant ON journal_lines(tenant_id);
CREATE INDEX idx_journal_lines_entity ON journal_lines(entity_type, entity_id);

-- ── PO Line Items ─────────────────────────────────────────────────────────
-- Extended PO line items (complements purchase_order_items with cost tracking).
CREATE TABLE IF NOT EXISTS po_line_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    po_id               UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    part_number         VARCHAR(100),
    description         TEXT NOT NULL DEFAULT '',
    quantity            DOUBLE PRECISION NOT NULL DEFAULT 1,
    unit_price          DOUBLE PRECISION NOT NULL DEFAULT 0,
    extended_price      DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost           DOUBLE PRECISION NOT NULL DEFAULT 0,
    received_quantity   DOUBLE PRECISION NOT NULL DEFAULT 0,
    invoiced_quantity   DOUBLE PRECISION NOT NULL DEFAULT 0,
    expected_date       TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(po_id, line_number)
);

CREATE INDEX idx_po_line_items_po ON po_line_items(po_id);
CREATE INDEX idx_po_line_items_product ON po_line_items(product_id);
CREATE INDEX idx_po_line_items_tenant ON po_line_items(tenant_id);

-- ── SO Line Items ─────────────────────────────────────────────────────────
-- Sales order line items.
CREATE TABLE IF NOT EXISTS so_line_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    so_id               UUID NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    part_number         VARCHAR(100),
    description         TEXT NOT NULL DEFAULT '',
    quantity            DOUBLE PRECISION NOT NULL DEFAULT 1,
    unit_price          DOUBLE PRECISION NOT NULL DEFAULT 0,
    extended_price      DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost           DOUBLE PRECISION NOT NULL DEFAULT 0,
    shipped_quantity    DOUBLE PRECISION NOT NULL DEFAULT 0,
    invoiced_quantity   DOUBLE PRECISION NOT NULL DEFAULT 0,
    requested_date      TIMESTAMPTZ,
    promised_date       TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(so_id, line_number)
);

CREATE INDEX idx_so_line_items_so ON so_line_items(so_id);
CREATE INDEX idx_so_line_items_product ON so_line_items(product_id);
CREATE INDEX idx_so_line_items_tenant ON so_line_items(tenant_id);

-- ── Customer Invoices ─────────────────────────────────────────────────────
-- Accounts receivable invoices sent to customers.
CREATE TABLE IF NOT EXISTS customer_invoices (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number      VARCHAR(50) NOT NULL,
    sales_order_id      UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    customer_id         UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'approved', 'paid', 'overdue', 'cancelled')),
    subtotal            DOUBLE PRECISION NOT NULL DEFAULT 0,
    tax                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    total               DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    due_date            TIMESTAMPTZ NOT NULL,
    paid_at             TIMESTAMPTZ,
    notes               TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, invoice_number)
);

CREATE INDEX idx_customer_invoices_tenant ON customer_invoices(tenant_id);
CREATE INDEX idx_customer_invoices_customer ON customer_invoices(customer_id);
CREATE INDEX idx_customer_invoices_status ON customer_invoices(tenant_id, status);
CREATE INDEX idx_customer_invoices_due ON customer_invoices(tenant_id, due_date)
    WHERE status NOT IN ('paid', 'cancelled');

-- ── Supplier Invoices ─────────────────────────────────────────────────────
-- Accounts payable invoices received from suppliers.
CREATE TABLE IF NOT EXISTS supplier_invoices (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number      VARCHAR(50) NOT NULL,
    po_id               UUID REFERENCES purchase_orders(id) ON DELETE SET NULL,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'received', 'approved', 'paid', 'disputed', 'cancelled')),
    subtotal            DOUBLE PRECISION NOT NULL DEFAULT 0,
    tax                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    total               DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    invoice_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_date            TIMESTAMPTZ NOT NULL,
    paid_at             TIMESTAMPTZ,
    notes               TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, invoice_number)
);

CREATE INDEX idx_supplier_invoices_tenant ON supplier_invoices(tenant_id);
CREATE INDEX idx_supplier_invoices_supplier ON supplier_invoices(supplier_id);
CREATE INDEX idx_supplier_invoices_status ON supplier_invoices(tenant_id, status);
CREATE INDEX idx_supplier_invoices_due ON supplier_invoices(tenant_id, due_date)
    WHERE status NOT IN ('paid', 'cancelled');

-- ── Supplier Payments ─────────────────────────────────────────────────────
-- Payments made to suppliers.
CREATE TABLE IF NOT EXISTS supplier_payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    payment_number      VARCHAR(50) NOT NULL,
    invoice_id          UUID REFERENCES supplier_invoices(id) ON DELETE SET NULL,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    amount              DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_method      VARCHAR(30) NOT NULL DEFAULT 'bank_transfer'
                        CHECK (payment_method IN ('bank_transfer', 'check', 'cash', 'credit_card', 'wire')),
    reference           VARCHAR(255),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'completed', 'failed', 'reversed')),
    paid_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes               TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, payment_number)
);

CREATE INDEX idx_supplier_payments_tenant ON supplier_payments(tenant_id);
CREATE INDEX idx_supplier_payments_supplier ON supplier_payments(supplier_id);
CREATE INDEX idx_supplier_payments_invoice ON supplier_payments(invoice_id);
CREATE INDEX idx_supplier_payments_status ON supplier_payments(tenant_id, status);

-- ── FX Rates ──────────────────────────────────────────────────────────────
-- Foreign exchange rates for multi-currency support.
CREATE TABLE IF NOT EXISTS fx_rates (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    from_currency       VARCHAR(3) NOT NULL,
    to_currency         VARCHAR(3) NOT NULL,
    rate                DOUBLE PRECISION NOT NULL,
    date                DATE NOT NULL,
    source              VARCHAR(100) NOT NULL DEFAULT 'manual',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, from_currency, to_currency, date)
);

CREATE INDEX idx_fx_rates_tenant ON fx_rates(tenant_id);
CREATE INDEX idx_fx_rates_pair ON fx_rates(from_currency, to_currency);
CREATE INDEX idx_fx_rates_date ON fx_rates(date DESC);

-- ── Tax Jurisdictions ─────────────────────────────────────────────────────
-- Tax rates by jurisdiction.
CREATE TABLE IF NOT EXISTS tax_jurisdictions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    region              VARCHAR(100),
    rate                DOUBLE PRECISION NOT NULL DEFAULT 0,
    tax_type            VARCHAR(30) NOT NULL DEFAULT 'sales'
                        CHECK (tax_type IN ('sales', 'vat', 'gst', 'withholding', 'excise', 'other')),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_tax_jurisdictions_tenant ON tax_jurisdictions(tenant_id);
CREATE INDEX idx_tax_jurisdictions_active ON tax_jurisdictions(tenant_id, is_active) WHERE is_active = TRUE;

-- ── Budget Allocations ────────────────────────────────────────────────────
-- Budget line items allocated to specific GL accounts.
CREATE TABLE IF NOT EXISTS budget_allocations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    budget_id           UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    gl_account_id       UUID NOT NULL REFERENCES gl_accounts(id) ON DELETE CASCADE,
    amount              DOUBLE PRECISION NOT NULL DEFAULT 0,
    spent               DOUBLE PRECISION NOT NULL DEFAULT 0,
    committed           DOUBLE PRECISION NOT NULL DEFAULT 0,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(budget_id, gl_account_id)
);

CREATE INDEX idx_budget_allocations_budget ON budget_allocations(budget_id);
CREATE INDEX idx_budget_allocations_account ON budget_allocations(gl_account_id);
CREATE INDEX idx_budget_allocations_tenant ON budget_allocations(tenant_id);
