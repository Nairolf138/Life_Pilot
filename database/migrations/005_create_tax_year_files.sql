-- Tax year assistant files prepared by LifePilot Admin.
-- Target database: PostgreSQL.

CREATE TABLE tax_year_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year INTEGER NOT NULL CHECK (tax_year >= 1900),
    income_year INTEGER NOT NULL CHECK (income_year >= 1900),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',
        'incomplete',
        'ready_for_review',
        'reviewed'
    )),
    summary_markdown TEXT,
    checklist_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    known_amounts_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    manual_prefilled_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, tax_year)
);

CREATE INDEX idx_tax_year_files_user_id ON tax_year_files(user_id);
CREATE INDEX idx_tax_year_files_tax_year ON tax_year_files(tax_year);
CREATE INDEX idx_tax_year_files_status ON tax_year_files(status);
