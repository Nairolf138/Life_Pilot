-- Document requirement preferences and category flags.
-- Target database: PostgreSQL.

ALTER TABLE categories
    ADD COLUMN IF NOT EXISTS requires_document BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS ignored_document_category_ids UUID[] NOT NULL DEFAULT '{}';

UPDATE categories
SET requires_document = true
WHERE type IN ('professional', 'administrative')
   OR name IN ('Assurances', 'Impôts', 'Travail', 'Administratif');
