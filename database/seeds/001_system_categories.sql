-- Seed the default Life Pilot system categories.
-- Target database: PostgreSQL.
--
-- Strategy:
-- 1. This seed creates a global catalogue of system category templates by
--    inserting them with user_id = NULL and is_system = true.
-- 2. When a user is created, the application can replicate this catalogue for
--    that user with the query shown at the bottom of this file. Keeping the
--    global catalogue makes the seed reusable even before an initial user
--    exists, while still allowing every user to customize their own copies.
-- 3. For a single initial user, run the replication query with that user's id
--    after this seed has been applied.

WITH system_categories (name, type) AS (
    VALUES
        ('Revenus', 'income'),
        ('Logement', 'expense'),
        ('Alimentation', 'expense'),
        ('Voiture', 'expense'),
        ('Santé', 'expense'),
        ('Assurances', 'expense'),
        ('Impôts', 'expense'),
        ('Abonnements', 'expense'),
        ('Loisirs', 'expense'),
        ('Restaurants / livraison', 'expense'),
        ('Animaux', 'expense'),
        ('Épargne', 'saving'),
        ('Investissement', 'investment'),
        ('Crypto', 'investment'),
        ('Travail', 'professional'),
        ('Administratif', 'administrative'),
        ('Retraits espèces', 'cash'),
        ('Virements internes', 'transfer'),
        ('Inconnu', 'unknown')
)
INSERT INTO categories (user_id, parent_id, name, type, is_system)
SELECT NULL, NULL, system_categories.name, system_categories.type, true
FROM system_categories
WHERE NOT EXISTS (
    SELECT 1
    FROM categories
    WHERE categories.user_id IS NULL
      AND categories.parent_id IS NULL
      AND categories.name = system_categories.name
      AND categories.is_system = true
);

-- Replication query to run when creating a user, or once for the initial user.
-- Replace '<user_uuid>' with the target users.id value.
--
-- INSERT INTO categories (user_id, parent_id, name, type, is_system)
-- SELECT '<user_uuid>'::uuid, NULL, template.name, template.type, true
-- FROM categories AS template
-- WHERE template.user_id IS NULL
--   AND template.parent_id IS NULL
--   AND template.is_system = true
--   AND NOT EXISTS (
--       SELECT 1
--       FROM categories AS existing
--       WHERE existing.user_id = '<user_uuid>'::uuid
--         AND existing.parent_id IS NULL
--         AND existing.name = template.name
--         AND existing.is_system = true
--   );
