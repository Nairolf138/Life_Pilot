-- Contracts and subscriptions followed by LifePilot Admin.
-- Target database: PostgreSQL.

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    contract_type TEXT NOT NULL CHECK (contract_type IN (
        'car_insurance',
        'home_insurance',
        'phone',
        'internet',
        'electricity',
        'streaming',
        'software',
        'telepeage',
        'bank_service',
        'other'
    )),
    name TEXT NOT NULL,
    reference TEXT,
    start_date DATE,
    end_date DATE,
    renewal_date DATE,
    notice_period_days INTEGER CHECK (notice_period_days IS NULL OR notice_period_days >= 0),
    monthly_cost NUMERIC(18, 2),
    yearly_cost NUMERIC(18, 2),
    payment_frequency TEXT CHECK (
        payment_frequency IS NULL
        OR payment_frequency IN ('monthly', 'yearly', 'quarterly', 'semiannual', 'one_time', 'other')
    ),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'terminated', 'to_review')),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE INDEX idx_contracts_user_id ON contracts(user_id);
CREATE INDEX idx_contracts_document_id ON contracts(document_id);
CREATE INDEX idx_contracts_renewal_date ON contracts(renewal_date);
CREATE INDEX idx_contracts_status ON contracts(status);
