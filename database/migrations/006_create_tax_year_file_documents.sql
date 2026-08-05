-- Links fiscal documents to annual tax year files.
-- Target database: PostgreSQL.

CREATE TABLE tax_year_file_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_year_file_id UUID NOT NULL REFERENCES tax_year_files(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    fiscal_document_type TEXT NOT NULL CHECK (fiscal_document_type IN (
        'tax_notice',
        'previous_tax_declaration',
        'bank_tax_document',
        'binance_export',
        'etoro_export',
        'income_proof',
        'manual_prefilled_declaration'
    )),
    source TEXT NOT NULL DEFAULT 'document_classification',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tax_year_file_id, document_id)
);

CREATE INDEX idx_tax_year_file_documents_tax_year_file_id
    ON tax_year_file_documents(tax_year_file_id);
CREATE INDEX idx_tax_year_file_documents_document_id
    ON tax_year_file_documents(document_id);
CREATE INDEX idx_tax_year_file_documents_fiscal_document_type
    ON tax_year_file_documents(fiscal_document_type);
