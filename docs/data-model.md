# Modèle de données

Ce document synthétise les tables PostgreSQL de Life Pilot, leur rôle fonctionnel, leurs champs structurants, leurs relations, les index importants et les données sensibles à protéger. Les tables ci-dessous sont issues des migrations SQL versionnées, avec la table `goals` décrite comme modèle cible lorsqu'elle n'est pas encore matérialisée par une migration.

## Vue d'ensemble relationnelle

- `users` est la racine multi-tenant : la majorité des tables métier portent un `user_id` et sont supprimées en cascade avec l'utilisateur.
- `connections` représente les autorisations et connecteurs externes ; `accounts` et certaines données importées y sont rattachés.
- `accounts`, `transactions`, `categories` et `categorization_rules` forment le cœur financier.
- `emails` et `documents` forment le cœur documentaire, avec des liens possibles vers `transactions`, `contracts`, `vehicles`, `vehicle_events` et `tax_year_files`.
- `contracts`, `vehicles`, `assets`, `goals` et `reminders` modélisent le suivi patrimonial, administratif et opérationnel.
- `audit_logs` trace les mutations et traitements automatisés.

## `users`

**Rôle**

Table centrale des utilisateurs et des préférences de compte. Elle sert de racine d'isolation des données personnelles.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `email` : adresse e-mail unique de connexion.
- `password_hash` : empreinte du mot de passe, nullable pour les modes d'authentification alternatifs.
- `mfa_enabled`, `passkey_enabled` : activation des facteurs de sécurité.
- `display_name` : nom affiché.
- `locale`, `timezone`, `currency_default` : préférences régionales et financières.
- `ignored_document_category_ids` : catégories pour lesquelles l'utilisateur ignore l'exigence documentaire.
- `created_at`, `updated_at` : horodatage de cycle de vie.

**Relations**

- Référencée par `connections`, `accounts`, `transactions`, `categories`, `categorization_rules`, `emails`, `documents`, `reminders`, `contracts`, `vehicles`, `assets`, `tax_year_files` et `goals` via `user_id`.
- Référencée par `audit_logs.user_id` avec conservation des logs en cas de suppression utilisateur (`ON DELETE SET NULL`).

**Index importants**

- Clé primaire sur `id`.
- Contrainte unique sur `email`.

**Données sensibles éventuelles**

- Très sensible : `email`, `password_hash`, statut MFA/passkey, préférences pouvant révéler la localisation (`locale`, `timezone`) et catégories ignorées.
- Ne jamais journaliser `password_hash` en clair dans les logs applicatifs.

## `connections`

**Rôle**

Stocke les connexions aux fournisseurs externes : banque, e-mail, plateformes patrimoniales ou autres intégrations.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire de la connexion.
- `provider`, `provider_type` : fournisseur et type de connecteur.
- `status` : état de connexion ou synchronisation.
- `last_sync_at`, `consent_expires_at` : suivi de synchronisation et expiration de consentement.
- `scopes` : permissions accordées.
- `metadata_json` : métadonnées fournisseur.
- `created_at`, `updated_at`.

**Relations**

- `connections.user_id` référence `users.id` en suppression cascade.
- `accounts.connection_id` référence `connections.id` avec mise à `NULL` si la connexion disparaît.

**Index importants**

- Clé primaire sur `id`.
- Index `idx_connections_provider` sur `provider`.

**Données sensibles éventuelles**

- Sensible : scopes, dates de consentement, statut d'accès, métadonnées fournisseur.
- Les secrets, tokens OAuth ou refresh tokens ne doivent pas être stockés en clair dans `metadata_json`.

## `accounts`

**Rôle**

Représente les comptes financiers importés ou saisis : comptes bancaires, cartes, comptes d'épargne, comptes d'investissement.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `connection_id` : connexion source optionnelle.
- `provider`, `account_type`, `name` : identification fonctionnelle du compte.
- `iban_masked` : IBAN masqué.
- `currency` : devise du compte.
- `balance_current`, `balance_available` : soldes.
- `external_id_hash` : identifiant fournisseur haché.
- `is_active`, `last_sync_at`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `connections.id` avec `ON DELETE SET NULL`.
- Référencée par `transactions.account_id` en cascade.
- Référencée par `assets.account_id` avec `ON DELETE SET NULL`.

**Index importants**

- Clé primaire sur `id`.
- Contrainte unique `(connection_id, external_id_hash)` pour éviter les doublons d'import.
- Index indirects via les tables dépendantes : `idx_transactions_account_id`, `idx_assets_account_id`.

**Données sensibles éventuelles**

- Très sensible : soldes, nom de compte, IBAN masqué, identifiants fournisseurs hachés.
- Les identifiants externes complets ne doivent pas être stockés sans hachage ou chiffrement.

## `transactions`

**Rôle**

Stocke les mouvements financiers normalisés, catégorisés et éventuellement rapprochés à des documents.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id`, `account_id` : propriétaire et compte source.
- `external_id_hash` : identifiant fournisseur haché.
- `booking_date`, `value_date` : dates comptables.
- `label_raw`, `label_clean`, `merchant_name` : libellés et marchand.
- `amount`, `currency`, `transaction_type` : montant et typologie.
- `category_id`, `subcategory_id` : catégorisation.
- `confidence_score` : confiance de catégorisation ou matching.
- `is_recurring`, `is_internal_transfer` : flags métier.
- `linked_document_id` : justificatif lié.
- `notes`, `raw_data_json`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `accounts.id` en cascade.
- Référence `categories.id` via `category_id` et `subcategory_id` avec `ON DELETE SET NULL`.
- Référence `documents.id` via `linked_document_id` avec `ON DELETE SET NULL`.
- Référencée par `documents.linked_transaction_id` avec `ON DELETE SET NULL`.

**Index importants**

- Index `idx_transactions_user_id` sur `user_id`.
- Index `idx_transactions_account_id` sur `account_id`.
- Index `idx_transactions_booking_date` sur `booking_date`.
- Index `idx_transactions_category_id` sur `category_id`.
- Contrainte unique `(account_id, external_id_hash)` pour l'idempotence d'import.

**Données sensibles éventuelles**

- Très sensible : montants, dates, marchands, libellés bruts, notes, données fournisseur brutes.
- `raw_data_json` peut contenir des informations bancaires détaillées et doit être filtré avant exposition API ou logs.

## `categories`

**Rôle**

Structure les catégories et sous-catégories de transactions, avec support des catégories système et personnalisées.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire pour les catégories personnalisées, nullable pour les catégories système.
- `parent_id` : hiérarchie de catégories.
- `name`, `type` : libellé et type métier.
- `monthly_budget` : budget mensuel optionnel.
- `is_system` : catégorie globale fournie par l'application.
- `requires_document` : exigence de justificatif.
- `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade pour les catégories utilisateur.
- Auto-référence `categories.parent_id` avec `ON DELETE SET NULL`.
- Référencée par `transactions.category_id`, `transactions.subcategory_id`, `categorization_rules.category_id` et `categorization_rules.subcategory_id`.

**Index importants**

- Clé primaire sur `id`.
- Contrainte unique `(user_id, parent_id, name)`.
- Index `idx_transactions_category_id` accélère les vues par catégorie côté transactions.

**Données sensibles éventuelles**

- Sensible modéré : budgets mensuels et catégories personnalisées peuvent révéler des habitudes ou contraintes financières.

## `categorization_rules`

**Rôle**

Décrit les règles utilisateur de catégorisation automatique des transactions.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `name`, `priority` : identification et ordre d'application.
- `match_type`, `pattern` : type de correspondance et motif.
- `provider_filter` : restriction fournisseur optionnelle.
- `amount_min`, `amount_max` : bornes de montant.
- `category_id`, `subcategory_id` : catégorie assignée.
- `confidence_score`, `is_active`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `categories.id` via `category_id` et `subcategory_id` avec `ON DELETE SET NULL`.

**Index importants**

- Clé primaire sur `id`.
- Aucun index dédié dans les migrations actuelles ; un index futur sur `(user_id, is_active, priority)` serait utile si le volume de règles augmente.

**Données sensibles éventuelles**

- Sensible : les motifs peuvent contenir des noms de marchands, employeurs, organismes médicaux ou libellés personnels.

## `documents`

**Rôle**

Indexe les documents stockés dans MinIO/S3 et porte les métadonnées nécessaires à l'extraction, au classement et au rapprochement métier.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `provider`, `document_type`, `title`, `issuer` : origine et classification.
- `issue_date`, `due_date`, `amount`, `currency` : informations extraites.
- `file_path`, `file_hash`, `mime_type` : référence de stockage et déduplication.
- `extracted_text`, `extraction_status`, `confidence_score` : résultat OCR/parsing.
- `linked_transaction_id`, `source_email_id` : liens d'origine ou rapprochement.
- `tags`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `transactions.id` via `linked_transaction_id` avec `ON DELETE SET NULL`.
- Référence `emails.id` via `source_email_id` avec `ON DELETE SET NULL`.
- Référencée par `transactions.linked_document_id`, `contracts.document_id`, `vehicle_events.document_id` et `tax_year_file_documents.document_id`.

**Index importants**

- Index `idx_documents_user_id` sur `user_id`.
- Index `idx_documents_file_hash` sur `file_hash`.
- Contrainte unique `(user_id, file_hash)` pour éviter les doublons par utilisateur.

**Données sensibles éventuelles**

- Très sensible : chemin de fichier, hash, texte extrait, émetteur, montants, dates, document fiscal, bancaire, médical, assurance ou administratif.
- `extracted_text` doit être considéré comme contenu documentaire complet et protégé comme le fichier source.

## `emails`

**Rôle**

Trace les e-mails ingérés, classifiés et utilisés comme source éventuelle de documents.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `provider` : fournisseur e-mail.
- `external_message_id_hash`, `thread_id_hash` : identifiants hachés.
- `from_email_hash`, `from_name` : expéditeur haché et nom affiché.
- `subject`, `received_at`, `snippet` : métadonnées et extrait.
- `classification`, `has_attachments`, `processed_at` : traitement applicatif.
- `raw_headers_json`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référencée par `documents.source_email_id` avec `ON DELETE SET NULL`.

**Index importants**

- Index `idx_emails_external_message_id_hash` sur `external_message_id_hash`.
- Contrainte unique `(provider, external_message_id_hash)`.

**Données sensibles éventuelles**

- Très sensible : sujet, extrait, nom d'expéditeur, en-têtes bruts et dates de réception.
- Les identifiants et adresses e-mail sont hachés lorsqu'ils proviennent du fournisseur.

## `contracts`

**Rôle**

Suit les contrats, abonnements et services récurrents : assurance, téléphonie, énergie, streaming, logiciels, services bancaires, etc.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `provider`, `contract_type`, `name`, `reference` : identification du contrat.
- `start_date`, `end_date`, `renewal_date`, `notice_period_days` : échéances.
- `monthly_cost`, `yearly_cost`, `payment_frequency` : coût et fréquence.
- `status` : `active`, `terminated` ou `to_review`.
- `document_id` : document contractuel lié.
- `notes`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `documents.id` avec `ON DELETE SET NULL`.
- Référencée par `vehicles.insurance_contract_id` avec `ON DELETE SET NULL`.

**Index importants**

- Index `idx_contracts_user_id` sur `user_id`.
- Index `idx_contracts_document_id` sur `document_id`.
- Index `idx_contracts_renewal_date` sur `renewal_date`.
- Index `idx_contracts_status` sur `status`.

**Données sensibles éventuelles**

- Sensible : références contrat, coûts, dates d'échéance, notes et fournisseur.

## `vehicles`

**Rôle**

Représente les véhicules suivis par l'utilisateur, leurs échéances administratives et leur contrat d'assurance.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `brand`, `model`, `version` : identification du véhicule.
- `registration_masked`, `vin_hash` : immatriculation masquée et VIN haché.
- `first_registration_date`, `mileage_current`, `mileage_updated_at` : historique d'usage.
- `technical_inspection_due_date` : échéance contrôle technique.
- `insurance_contract_id` : contrat d'assurance lié.
- `maintenance_notes`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `contracts.id` via `insurance_contract_id` avec `ON DELETE SET NULL`.
- Référencée par `vehicle_events.vehicle_id` en cascade.

**Index importants**

- Index `idx_vehicles_user_id` sur `user_id`.
- Index `idx_vehicles_insurance_contract_id` sur `insurance_contract_id`.
- Index `idx_vehicles_technical_inspection_due_date` sur `technical_inspection_due_date`.

**Données sensibles éventuelles**

- Sensible : véhicule possédé, immatriculation masquée, VIN haché, kilométrage, échéances et notes d'entretien.

## `vehicle_events`

**Rôle**

Historise les événements d'un véhicule : entretien, réparation, carburant, assurance, contrôle technique et prochaines échéances.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `vehicle_id` : véhicule concerné.
- `event_type`, `event_date`, `title` : type, date et libellé.
- `mileage`, `description`, `cost` : contexte d'événement.
- `document_id` : justificatif associé.
- `next_due_date`, `next_due_mileage` : prochaine échéance.
- `created_at`.

**Relations**

- Référence `vehicles.id` en cascade.
- Référence `documents.id` avec `ON DELETE SET NULL`.

**Index importants**

- Index `idx_vehicle_events_vehicle_id` sur `vehicle_id`.
- Index `idx_vehicle_events_document_id` sur `document_id`.
- Index `idx_vehicle_events_event_date` sur `event_date`.
- Index `idx_vehicle_events_next_due_date` sur `next_due_date`.

**Données sensibles éventuelles**

- Sensible : réparations, coûts, kilométrage, documents liés et habitudes d'usage du véhicule.

## `assets`

**Rôle**

Stocke les actifs patrimoniaux et positions de portefeuille : cash, actions, ETF, crypto, fonds, obligations ou autres actifs.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `provider` : source de la position.
- `account_id` : compte financier lié optionnel.
- `asset_type`, `symbol`, `name` : typologie et identification.
- `quantity`, `average_buy_price`, `current_price` : valorisation unitaire.
- `currency`, `current_value`, `pnl_unrealized` : devise, valeur courante et plus-value latente.
- `last_price_sync_at`, `raw_data_json`, `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Référence `accounts.id` avec `ON DELETE SET NULL`.

**Index importants**

- Index `idx_assets_user_id` sur `user_id`.
- Index `idx_assets_account_id` sur `account_id`.
- Index `idx_assets_asset_type` sur `asset_type`.
- Index `idx_assets_symbol` sur `symbol`.
- Index `idx_assets_currency` sur `currency`.

**Données sensibles éventuelles**

- Très sensible : patrimoine, quantités, prix d'achat, valeur courante, plus-values latentes et données fournisseur brutes.

## `goals`

**Rôle**

Table cible pour suivre les objectifs financiers ou patrimoniaux d'un utilisateur : épargne, voyage, achat, remboursement, investissement ou objectif de patrimoine net.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `name` : nom de l'objectif.
- `goal_type` : type fonctionnel de l'objectif.
- `target_amount`, `current_amount` : montant cible et montant atteint.
- `target_date` : échéance souhaitée.
- `priority` : priorité d'affichage ou d'arbitrage.
- `status` : état de l'objectif.
- `created_at`, `updated_at`.

**Relations**

- Devrait référencer `users.id` en cascade.
- Peut alimenter des `reminders` via `source_type = 'goal'` et `source_id = goals.id`, sans contrainte polymorphe directe.

**Index importants**

- À prévoir : index sur `user_id` pour les listes par utilisateur.
- À prévoir : index sur `(user_id, status)` pour les tableaux de bord.
- À prévoir : index sur `target_date` pour les échéances.

**Données sensibles éventuelles**

- Très sensible : objectifs d'épargne, patrimoine cible, priorités financières et montants disponibles.

## `reminders`

**Rôle**

Gère les rappels utilisateur et notifications issues de sources diverses : contrat, document, véhicule, objectif ou saisie manuelle.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `source_type`, `source_id` : source polymorphe optionnelle.
- `title`, `description` : contenu du rappel.
- `due_date`, `reminder_date` : échéance et date de notification.
- `severity` : niveau d'importance.
- `status` : état du rappel.
- `recurrence_rule` : règle de récurrence.
- `notification_channels` : canaux de notification.
- `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Relation polymorphe via `source_type` / `source_id` vers des entités comme `documents`, `contracts`, `vehicles`, `vehicle_events`, `goals` ou `tax_year_files` ; aucune clé étrangère directe ne peut garantir toutes ces cibles.

**Index importants**

- Index `idx_reminders_due_date` sur `due_date`.
- Un index futur sur `(user_id, status, due_date)` serait utile pour les vues utilisateur.

**Données sensibles éventuelles**

- Sensible : titres, descriptions, échéances administratives, canaux de notification et références à des sources personnelles.

## `audit_logs`

**Rôle**

Journalise les actions importantes : création, modification, suppression logique, import, catégorisation et rapprochement.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : utilisateur concerné, nullable si supprimé.
- `actor` : acteur (`user`, `system`, `worker`, `n8n`).
- `action` : type d'action contrôlé.
- `entity_type`, `entity_id` : cible métier.
- `before_json`, `after_json` : état avant/après.
- `reason` : justification.
- `created_at`, `updated_at`.

**Relations**

- Référence `users.id` avec `ON DELETE SET NULL`.
- Référence polymorphe logique vers l'entité cible via `entity_type` / `entity_id`, sans contrainte FK directe.

**Index importants**

- Index `idx_audit_logs_user_id` sur `user_id`.
- Index `idx_audit_logs_entity` sur `(entity_type, entity_id)`.
- Index `idx_audit_logs_created_at` sur `created_at`.

**Données sensibles éventuelles**

- Très sensible : `before_json` et `after_json` peuvent contenir des copies de données financières, documentaires ou personnelles.
- Les journaux d'audit doivent faire l'objet d'une politique de rétention, masquage et accès restreint.

## `tax_year_files`

**Rôle**

Agrège la préparation fiscale annuelle d'un utilisateur : statut du dossier, synthèse, checklist, montants connus et données préremplies manuellement.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `user_id` : propriétaire.
- `tax_year` : année fiscale déclarée.
- `income_year` : année des revenus concernés.
- `status` : `draft`, `incomplete`, `ready_for_review` ou `reviewed`.
- `summary_markdown` : synthèse lisible du dossier.
- `checklist_json` : checklist structurée.
- `known_amounts_json` : montants détectés ou calculés.
- `manual_prefilled_data_json` : données préremplies manuellement.
- `created_at`, `updated_at`.

**Relations**

- Référence `users.id` en cascade.
- Reliée aux `documents` via la table d'association `tax_year_file_documents`.
- Peut être référencée par `reminders.source_type = 'tax_year_file'` et `source_id`.

**Index importants**

- Index `idx_tax_year_files_user_id` sur `user_id`.
- Index `idx_tax_year_files_tax_year` sur `tax_year`.
- Index `idx_tax_year_files_status` sur `status`.
- Contrainte unique `(user_id, tax_year)`.

**Données sensibles éventuelles**

- Extrêmement sensible : informations fiscales, montants, synthèses, checklist, données préremplies et documents associés.
- Les champs JSON peuvent contenir des revenus, références fiscales, comptes financiers ou informations familiales.

## Table d'association `tax_year_file_documents`

Même si elle n'est pas listée comme table métier principale, elle est nécessaire au modèle fiscal.

**Rôle**

Associe les documents utiles à un dossier fiscal annuel et précise leur type fiscal.

**Champs principaux**

- `id` : identifiant UUID primaire.
- `tax_year_file_id` : dossier fiscal concerné.
- `document_id` : document associé.
- `fiscal_document_type` : type de document fiscal.
- `source` : origine de l'association.
- `created_at`, `updated_at`.

**Relations**

- Référence `tax_year_files.id` en cascade.
- Référence `documents.id` en cascade.

**Index importants**

- Index `idx_tax_year_file_documents_tax_year_file_id`.
- Index `idx_tax_year_file_documents_document_id`.
- Index `idx_tax_year_file_documents_fiscal_document_type`.
- Contrainte unique `(tax_year_file_id, document_id)`.

**Données sensibles éventuelles**

- Très sensible : association entre documents et fiscalité annuelle, types fiscaux et provenance de classification.
