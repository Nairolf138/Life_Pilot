-- Initial LifePilot Admin schema.
-- Target database: PostgreSQL.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    mfa_enabled BOOLEAN NOT NULL DEFAULT false,
    passkey_enabled BOOLEAN NOT NULL DEFAULT false,
    display_name TEXT,
    locale TEXT NOT NULL DEFAULT 'fr-FR',
    timezone TEXT NOT NULL DEFAULT 'Europe/Paris',
    currency_default CHAR(3) NOT NULL DEFAULT 'EUR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    status TEXT NOT NULL,
    last_sync_at TIMESTAMPTZ,
    consent_expires_at TIMESTAMPTZ,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES connections(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    account_type TEXT NOT NULL,
    name TEXT NOT NULL,
    iban_masked TEXT,
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    balance_current NUMERIC(18, 2),
    balance_available NUMERIC(18, 2),
    external_id_hash TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (connection_id, external_id_hash)
);

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    monthly_budget NUMERIC(18, 2),
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, parent_id, name)
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    external_id_hash TEXT,
    booking_date DATE NOT NULL,
    value_date DATE,
    label_raw TEXT NOT NULL,
    label_clean TEXT,
    merchant_name TEXT,
    amount NUMERIC(18, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    transaction_type TEXT,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    subcategory_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    confidence_score NUMERIC(5, 4),
    is_recurring BOOLEAN NOT NULL DEFAULT false,
    is_internal_transfer BOOLEAN NOT NULL DEFAULT false,
    linked_document_id UUID,
    notes TEXT,
    raw_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, external_id_hash)
);

CREATE TABLE categorization_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    match_type TEXT NOT NULL,
    pattern TEXT NOT NULL,
    provider_filter TEXT,
    amount_min NUMERIC(18, 2),
    amount_max NUMERIC(18, 2),
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    subcategory_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    confidence_score NUMERIC(5, 4),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    external_message_id_hash TEXT NOT NULL,
    thread_id_hash TEXT,
    from_email_hash TEXT,
    from_name TEXT,
    subject TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    snippet TEXT,
    classification TEXT,
    has_attachments BOOLEAN NOT NULL DEFAULT false,
    processed_at TIMESTAMPTZ,
    raw_headers_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, external_message_id_hash)
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT,
    document_type TEXT NOT NULL,
    title TEXT NOT NULL,
    issuer TEXT,
    issue_date DATE,
    due_date DATE,
    amount NUMERIC(18, 2),
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT,
    extracted_text TEXT,
    extraction_status TEXT,
    confidence_score NUMERIC(5, 4),
    linked_transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    source_email_id UUID REFERENCES emails(id) ON DELETE SET NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, file_hash)
);

ALTER TABLE transactions
    ADD CONSTRAINT transactions_linked_document_id_fkey
    FOREIGN KEY (linked_document_id) REFERENCES documents(id) ON DELETE SET NULL;

CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type TEXT,
    source_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    reminder_date DATE,
    severity TEXT NOT NULL DEFAULT 'info',
    status TEXT NOT NULL DEFAULT 'pending',
    recurrence_rule TEXT,
    notification_channels TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor TEXT NOT NULL CHECK (actor IN ('user', 'system', 'worker', 'n8n')),
    action TEXT NOT NULL CHECK (action IN (
        'creation',
        'modification',
        'logical_deletion',
        'import',
        'categorization',
        'matching'
    )),
    entity_type TEXT NOT NULL,
    entity_id UUID,
    before_json JSONB,
    after_json JSONB,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_booking_date ON transactions(booking_date);
CREATE INDEX idx_transactions_category_id ON transactions(category_id);
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_emails_external_message_id_hash ON emails(external_message_id_hash);
CREATE INDEX idx_connections_provider ON connections(provider);
CREATE INDEX idx_reminders_due_date ON reminders(due_date);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
