-- CRM and sales tables for Sensei ERP
--
-- This migration adds CRM-related tables for accounts, contacts,
-- and sales opportunities. These support the customer relationship
-- management workflow.

-- ── Accounts ───────────────────────────────────────────────────────────────
-- Organizations (customers, suppliers, partners) in the CRM system.
CREATE TABLE IF NOT EXISTS accounts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    account_type    VARCHAR(30) NOT NULL DEFAULT 'customer'
                    CHECK (account_type IN ('customer', 'supplier', 'partner', 'prospect', 'other')),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'inactive', 'churned', 'suspended')),
    tier            VARCHAR(20)
                    CHECK (tier IS NULL OR tier IN ('platinum', 'gold', 'silver', 'bronze')),
    industry        VARCHAR(100),
    website         VARCHAR(500),
    phone           VARCHAR(50),
    email           VARCHAR(320),
    address_line1   VARCHAR(255),
    address_line2   VARCHAR(255),
    city            VARCHAR(100),
    state           VARCHAR(100),
    postal_code     VARCHAR(20),
    country         VARCHAR(100),
    annual_revenue  DOUBLE PRECISION,
    parent_id       UUID REFERENCES accounts(id) ON DELETE SET NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_accounts_tenant ON accounts(tenant_id);
CREATE INDEX idx_accounts_type ON accounts(tenant_id, account_type);
CREATE INDEX idx_accounts_status ON accounts(tenant_id, status);
CREATE INDEX idx_accounts_tier ON accounts(tenant_id, tier);
CREATE INDEX idx_accounts_parent ON accounts(parent_id);

-- ── Contacts ──────────────────────────────────────────────────────────────
-- Individual people associated with accounts.
CREATE TABLE IF NOT EXISTS contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    first_name      VARCHAR(255) NOT NULL,
    last_name       VARCHAR(255) NOT NULL,
    email           VARCHAR(320),
    phone           VARCHAR(50),
    mobile          VARCHAR(50),
    job_title       VARCHAR(255),
    account_id      UUID REFERENCES accounts(id) ON DELETE SET NULL,
    notes           TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contacts_tenant ON contacts(tenant_id);
CREATE INDEX idx_contacts_account ON contacts(account_id);
CREATE INDEX idx_contacts_email ON contacts(tenant_id, email);
CREATE INDEX idx_contacts_name ON contacts(tenant_id, last_name, first_name);

-- ── Account Contacts ──────────────────────────────────────────────────────
-- Junction table linking accounts to contacts with role information.
CREATE TABLE IF NOT EXISTS account_contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    account_id      UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    contact_id      UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    role            VARCHAR(100),
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, contact_id)
);

CREATE INDEX idx_account_contacts_account ON account_contacts(account_id);
CREATE INDEX idx_account_contacts_contact ON account_contacts(contact_id);
CREATE INDEX idx_account_contacts_primary ON account_contacts(account_id) WHERE is_primary = TRUE;

-- ── Opportunities ─────────────────────────────────────────────────────────
-- Sales opportunities tracking pipeline and revenue forecasting.
CREATE TABLE IF NOT EXISTS opportunities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(500) NOT NULL,
    stage           VARCHAR(30) NOT NULL DEFAULT 'prospecting'
                    CHECK (stage IN ('prospecting', 'qualification', 'needs_analysis',
                           'value_proposition', 'negotiation', 'closed_won', 'closed_lost')),
    amount          DOUBLE PRECISION NOT NULL DEFAULT 0,
    probability     INT NOT NULL DEFAULT 0 CHECK (probability BETWEEN 0 AND 100),
    close_date      TIMESTAMPTZ,
    account_id      UUID REFERENCES accounts(id) ON DELETE SET NULL,
    contact_id      UUID REFERENCES contacts(id) ON DELETE SET NULL,
    owner_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    description     TEXT,
    lost_reason     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_opportunities_tenant ON opportunities(tenant_id);
CREATE INDEX idx_opportunities_stage ON opportunities(tenant_id, stage);
CREATE INDEX idx_opportunities_account ON opportunities(account_id);
CREATE INDEX idx_opportunities_owner ON opportunities(owner_id);
CREATE INDEX idx_opportunities_close_date ON opportunities(tenant_id, close_date);
