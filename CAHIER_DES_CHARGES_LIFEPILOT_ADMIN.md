# Cahier des charges — LifePilot Admin

> Assistant personnel de vie administrative et financière.
>
> Objectif : centraliser, analyser, classer, rapprocher et surveiller automatiquement les données financières, administratives et patrimoniales d’un particulier, avec une interface unique, fiable, sécurisée et réellement utile au quotidien.

---

## 1. Résumé du projet

**LifePilot Admin** est une application personnelle auto-hébergée destinée à remplacer les fichiers Excel mensuels, les rappels dispersés, les recherches de factures dans les emails et les suivis incomplets d’applications financières généralistes.

Le système doit devenir un **tableau de bord personnel global** capable de :

- récupérer automatiquement les transactions bancaires ;
- récupérer les soldes des comptes ;
- importer les positions crypto, actions et brokers ;
- analyser les emails pour détecter factures, contrats, échéances et documents administratifs ;
- rapprocher automatiquement une facture reçue par email avec une transaction bancaire ;
- classer les dépenses avec des catégories personnalisées ;
- détecter les abonnements, charges fixes, variations inhabituelles et dérives budgétaires ;
- suivre les objectifs financiers ;
- préparer un dossier fiscal annuel à vérifier manuellement ;
- surveiller les échéances administratives : contrôle technique, assurance, bail, impôts, abonnements, renouvellements, résiliations ;
- notifier uniquement ce qui demande une action réelle.

Le projet doit rester **personnel, privé, vérifiable et contrôlable**. L’automatisation doit aider, pas décider à la place de l’utilisateur. Les actions sensibles doivent toujours rester soumises à validation humaine.

---

## 2. Vision produit

### 2.1 Vision courte

Créer un assistant personnel capable de répondre à la question :

> “Où j’en suis financièrement, administrativement, fiscalement et patrimonialement, et qu’est-ce que je dois faire maintenant ?”

### 2.2 Vision longue

LifePilot Admin doit devenir une sorte de **secrétaire administratif et financier personnel**, capable de lire les signaux faibles dans les comptes, les emails et les documents, puis de produire une synthèse claire :

- argent disponible ;
- dépenses du mois ;
- factures reçues ;
- factures payées ;
- justificatifs manquants ;
- démarches à prévoir ;
- échéances à venir ;
- état du patrimoine ;
- opportunités d’économie ;
- risques administratifs ;
- préparation fiscale annuelle.

Le système doit viser le ratio suivant :

```text
80 % automatisé
20 % validation humaine
0 % illusion magique irresponsable
```

---

## 3. Principes directeurs

### 3.1 Local-first et self-hosted

Les données personnelles doivent rester autant que possible dans l’infrastructure contrôlée par l’utilisateur : VPS privé, machine locale, NAS ou serveur maison.

### 3.2 Lecture seule par défaut

Tous les connecteurs financiers doivent fonctionner en **lecture seule** lors des premières versions.

Exemples :

- banque : consultation comptes, soldes, transactions ;
- Binance : lecture soldes, historique, prix ;
- eToro : lecture portefeuille et performance ;
- Gmail : lecture emails et pièces jointes ;
- aucun virement ;
- aucun ordre d’achat/vente ;
- aucune télédéclaration automatique ;
- aucune résiliation automatique.

### 3.3 Humain validateur

L’assistant peut :

- proposer ;
- classer ;
- préremplir ;
- résumer ;
- rappeler ;
- détecter.

Il ne doit pas :

- envoyer une déclaration fiscale seul ;
- prendre un rendez-vous critique sans confirmation ;
- effectuer une opération bancaire ;
- vendre ou acheter des actifs ;
- supprimer un document sans validation.

### 3.4 Traçabilité totale

Chaque action automatique doit être justifiable :

- source de la donnée ;
- date d’import ;
- règle utilisée ;
- score de confiance ;
- validation ou correction humaine ;
- historique des modifications.

### 3.5 Notifications rares mais utiles

Le système ne doit pas devenir une usine à notifications inutiles.

Une notification doit être envoyée uniquement si :

- une action est requise ;
- une échéance approche ;
- une anomalie est détectée ;
- un risque financier ou administratif existe ;
- une validation humaine est nécessaire.

---

## 4. Utilisateur cible

### 4.1 Profil principal

Particulier français ayant plusieurs sources de données :

- comptes bancaires Crédit Mutuel ;
- contrats d’assurance ;
- emails contenant factures, notifications et documents administratifs ;
- compte Binance ;
- compte eToro ;
- compte télépéage Fulli ;
- abonnements divers ;
- véhicule personnel avec échéances : contrôle technique, assurance, entretien ;
- obligations fiscales annuelles ;
- suivi actuellement fait en tableur manuel.

### 4.2 Problèmes à résoudre

- Perte de temps à maintenir un tableau Excel mensuel.
- Catégorisation automatique insuffisante dans les apps existantes.
- Vision éclatée entre banque, crypto, actions, emails et administrations.
- Risque d’oublier des démarches importantes.
- Difficulté à relier une facture à un paiement.
- Difficulté à obtenir un état global fiable du patrimoine.
- Manque de conseils personnalisés basés sur les habitudes réelles.

---

## 5. Périmètre fonctionnel global

### 5.1 Modules principaux

1. **Dashboard global**
2. **Agrégation bancaire**
3. **Catégorisation des transactions**
4. **Analyse budgétaire**
5. **Gestion des documents et factures**
6. **Rapprochement facture / transaction**
7. **Suivi des contrats et abonnements**
8. **Suivi véhicule**
9. **Suivi patrimoine : crypto, actions, cash**
10. **Assistant fiscal annuel**
11. **Moteur de rappels et notifications**
12. **Assistant conversationnel privé**
13. **Administration système et sécurité**

---

## 6. Périmètre hors V1

Les fonctions suivantes sont explicitement hors périmètre de la première version stable :

- virement bancaire automatique ;
- trading automatique ;
- déclaration d’impôts envoyée automatiquement ;
- résiliation automatique d’abonnements ;
- scraping agressif de sites administratifs protégés ;
- stockage de mots de passe de portails publics en clair ;
- optimisation fiscale avancée sans validation humaine ;
- conseil financier réglementé présenté comme une vérité absolue.

Ces fonctions pourront être étudiées plus tard, mais seulement avec une couche de validation, d’audit et de sécurité beaucoup plus forte.

---

## 7. Contraintes réglementaires et techniques connues

### 7.1 Accès bancaire

L’accès aux comptes bancaires devra passer par un fournisseur d’Open Banking compatible PSD2, par exemple :

- GoCardless Bank Account Data ;
- Powens ;
- Bridge ;
- autre agrégateur compatible avec les banques françaises.

Avec GoCardless Bank Account Data, l’accès peut fournir comptes, transactions et soldes, avec jusqu’à 24 mois d’historique selon les cas, mais l’accès continu est limité à une période de consentement, typiquement 90 jours. Le système doit donc gérer le **renouvellement périodique du consentement bancaire**.

### 7.2 FranceConnect

FranceConnect sert principalement à s’identifier auprès de services publics ou privés compatibles. Il ne doit pas être considéré comme une API universelle permettant de récupérer automatiquement tous les documents administratifs d’un particulier.

### 7.3 API fiscales

Les APIs fiscales publiques disponibles sont généralement destinées à des administrations, organismes publics ou entités éligibles dans le cadre de missions réglementées. Le projet ne doit donc pas supposer qu’il pourra accéder directement aux données impots.gouv comme une application personnelle classique.

### 7.4 Déclaration d’impôts

L’assistant fiscal doit être conçu comme un module de **préparation, contrôle et aide à la déclaration**, pas comme un système de télédéclaration autonome.

Il doit :

- centraliser les revenus et justificatifs connus ;
- repérer les montants utiles ;
- préparer une synthèse annuelle ;
- signaler les points à vérifier ;
- aider à comparer avec la déclaration préremplie ;
- générer une checklist.

Il ne doit pas :

- envoyer la déclaration seul ;
- garantir le montant de l’impôt ;
- remplacer un expert fiscal ;
- contourner impots.gouv.

---

## 8. Architecture cible

### 8.1 Architecture générale

```text
Sources externes
  ├── Banque / Open Banking
  ├── Gmail / emails
  ├── Binance API
  ├── eToro API
  ├── Exports CSV / PDF manuels
  ├── Documents administratifs
  └── Saisie utilisateur minimale
        ↓
Connecteurs et automatisations
  ├── n8n workflows
  ├── workers backend
  ├── cron jobs
  └── webhooks
        ↓
Base centrale
  ├── PostgreSQL
  ├── stockage fichiers chiffré
  └── index vectoriel optionnel
        ↓
Moteurs applicatifs
  ├── catégorisation
  ├── rapprochement
  ├── détection d’anomalies
  ├── rappels
  ├── fiscal assistant
  └── assistant IA
        ↓
Interfaces
  ├── dashboard web
  ├── mobile responsive
  ├── notifications email / Telegram / push
  └── exports PDF / CSV / Markdown
```

### 8.2 Stack technique recommandée

#### Option recommandée

```text
Frontend       : Next.js / React / TypeScript
Backend        : FastAPI Python ou NestJS TypeScript
Base données   : PostgreSQL
Automatisation : n8n
Stockage docs  : MinIO S3 local ou dossier chiffré
Queue jobs     : Redis + BullMQ / Celery / RQ
OCR            : Tesseract ou service OCR local/cloud optionnel
IA             : LLM configurable, local ou API
Vector DB      : Qdrant optionnel
Déploiement    : Docker Compose
Reverse proxy  : Caddy, Traefik ou Nginx
Auth           : session sécurisée + 2FA / passkey si possible
```

#### Pourquoi ce choix

- **n8n** est excellent pour l’orchestration, les emails, les webhooks et les tâches périodiques.
- **PostgreSQL** offre une base robuste, requêtable et durable.
- **Next.js** permet un dashboard moderne et agréable.
- **FastAPI** est très efficace pour les traitements Python, OCR, parsing, IA et data.
- **Docker Compose** simplifie le déploiement personnel.
- **Qdrant** devient utile plus tard pour rechercher dans les documents et poser des questions à l’assistant.

---

## 9. Structure recommandée du repo

```text
lifepilot-admin/
├── README.md
├── CAHIER_DES_CHARGES.md
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── security.md
│   ├── data-model.md
│   ├── workflows-n8n.md
│   ├── fiscal-assistant.md
│   └── roadmap.md
├── apps/
│   ├── web/
│   │   ├── src/
│   │   └── package.json
│   └── api/
│       ├── app/
│       ├── tests/
│       └── pyproject.toml
├── packages/
│   ├── shared-types/
│   └── rules-engine/
├── workflows/
│   ├── n8n/
│   │   ├── gmail-ingestion.json
│   │   ├── bank-sync.json
│   │   ├── documents-extraction.json
│   │   └── notifications.json
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schema.sql
├── scripts/
│   ├── import_csv.py
│   ├── backup.sh
│   └── restore.sh
├── storage/
│   └── .gitkeep
└── tests/
    ├── fixtures/
    └── integration/
```

---

## 10. Modèle de données cible

### 10.1 Table `users`

Même si l’application est personnelle, prévoir une table utilisateur permet d’évoluer proprement.

```text
users
- id
- email
- display_name
- locale
- timezone
- currency_default
- created_at
- updated_at
```

### 10.2 Table `connections`

Stocke les connexions aux fournisseurs externes.

```text
connections
- id
- user_id
- provider
- provider_type
- status
- last_sync_at
- consent_expires_at
- scopes
- metadata_json
- created_at
- updated_at
```

Exemples de `provider` :

```text
credit_mutuel
gocardless
powens
gmail
binance
etoro
fulli
impots_manual
ants_manual
```

Exemples de `provider_type` :

```text
bank
email
crypto
broker
admin
subscription
manual
```

### 10.3 Table `accounts`

```text
accounts
- id
- user_id
- connection_id
- provider
- account_type
- name
- iban_masked
- currency
- balance_current
- balance_available
- external_id_hash
- is_active
- last_sync_at
- created_at
- updated_at
```

Types possibles :

```text
checking
savings
credit_card
loan
crypto_wallet
brokerage
cash
unknown
```

### 10.4 Table `transactions`

```text
transactions
- id
- user_id
- account_id
- external_id_hash
- booking_date
- value_date
- label_raw
- label_clean
- merchant_name
- amount
- currency
- transaction_type
- category_id
- subcategory_id
- confidence_score
- is_recurring
- is_internal_transfer
- linked_document_id
- notes
- raw_data_json
- created_at
- updated_at
```

### 10.5 Table `categories`

```text
categories
- id
- user_id
- parent_id
- name
- type
- monthly_budget
- is_system
- created_at
- updated_at
```

Catégories de départ :

```text
Revenus
Logement
Alimentation
Voiture
Santé
Assurances
Impôts
Abonnements
Loisirs
Restaurants / livraison
Animaux
Épargne
Investissement
Crypto
Travail
Administratif
Retraits espèces
Virements internes
Inconnu
```

### 10.6 Table `categorization_rules`

```text
categorization_rules
- id
- user_id
- name
- priority
- match_type
- pattern
- provider_filter
- amount_min
- amount_max
- category_id
- subcategory_id
- confidence_score
- is_active
- created_at
- updated_at
```

Types de correspondance :

```text
contains
regex
merchant_exact
amount_range
provider_specific
ai_suggested
manual_learning
```

### 10.7 Table `documents`

```text
documents
- id
- user_id
- provider
- document_type
- title
- issuer
- issue_date
- due_date
- amount
- currency
- file_path
- file_hash
- mime_type
- extracted_text
- extraction_status
- confidence_score
- linked_transaction_id
- source_email_id
- tags
- created_at
- updated_at
```

Types de document :

```text
invoice
receipt
tax_notice
tax_declaration
insurance_contract
insurance_notice
rent_notice
vehicle_document
technical_inspection
bank_statement
subscription_notice
health_document
other
```

### 10.8 Table `emails`

```text
emails
- id
- user_id
- provider
- external_message_id_hash
- thread_id_hash
- from_email_hash
- from_name
- subject
- received_at
- snippet
- classification
- has_attachments
- processed_at
- raw_headers_json
- created_at
```

### 10.9 Table `contracts`

```text
contracts
- id
- user_id
- provider
- contract_type
- name
- reference
- start_date
- end_date
- renewal_date
- notice_period_days
- monthly_cost
- yearly_cost
- payment_frequency
- status
- document_id
- notes
- created_at
- updated_at
```

Types :

```text
rent
home_insurance
car_insurance
health_insurance
phone
internet
electricity
streaming
software
telepeage
bank_service
vehicle_maintenance
other
```

### 10.10 Table `vehicles`

```text
vehicles
- id
- user_id
- brand
- model
- version
- registration_masked
- vin_hash
- first_registration_date
- mileage_current
- mileage_updated_at
- technical_inspection_due_date
- insurance_contract_id
- maintenance_notes
- created_at
- updated_at
```

### 10.11 Table `vehicle_events`

```text
vehicle_events
- id
- vehicle_id
- event_type
- event_date
- mileage
- title
- description
- cost
- document_id
- next_due_date
- next_due_mileage
- created_at
```

Types :

```text
technical_inspection
maintenance
oil_change
brakes
tires
insurance
repair
fuel
other
```

### 10.12 Table `assets`

```text
assets
- id
- user_id
- provider
- account_id
- asset_type
- symbol
- name
- quantity
- average_buy_price
- current_price
- currency
- current_value
- pnl_unrealized
- last_price_sync_at
- raw_data_json
- created_at
- updated_at
```

Types :

```text
cash
stock
etf
crypto
fund
bond
other
```

### 10.13 Table `goals`

```text
goals
- id
- user_id
- name
- goal_type
- target_amount
- current_amount
- target_date
- priority
- status
- created_at
- updated_at
```

Exemples :

```text
Épargne de sécurité
Voyage
Achat matériel
Remboursement crédit
Investissement long terme
Patrimoine net cible
```

### 10.14 Table `reminders`

```text
reminders
- id
- user_id
- source_type
- source_id
- title
- description
- due_date
- reminder_date
- severity
- status
- recurrence_rule
- notification_channels
- created_at
- updated_at
```

Sévérités :

```text
info
warning
urgent
critical
```

### 10.15 Table `audit_logs`

```text
audit_logs
- id
- user_id
- actor
- action
- entity_type
- entity_id
- before_json
- after_json
- reason
- created_at
```

---

## 11. Module Dashboard global

### 11.1 Objectif

Afficher en une page l’état réel de la vie financière et administrative.

### 11.2 Contenu minimum

Le dashboard doit afficher :

- solde total bancaire ;
- solde par compte ;
- patrimoine total estimé ;
- cash disponible ;
- crypto total ;
- actions total ;
- dettes / crédits connus ;
- dépenses du mois ;
- revenus du mois ;
- épargne du mois ;
- reste à vivre estimé ;
- top catégories de dépenses ;
- factures non rapprochées ;
- documents récents ;
- alertes importantes ;
- échéances à 7, 30, 60 et 90 jours ;
- objectifs financiers.

### 11.3 Exemple de synthèse attendue

```text
Juillet 2026

Revenus : 2 050 €
Dépenses : 1 420 €
Épargne estimée : 630 €
Reste à vivre jusqu’à la fin du mois : 480 €

Points d’attention :
- Assurance auto renouvelée dans 42 jours.
- Contrôle technique BMW à vérifier : aucune date enregistrée.
- 3 transactions sans catégorie fiable.
- 2 factures reçues non rapprochées.
- Dépenses restaurants/livraison supérieures de 28 % à la moyenne 6 mois.
```

---

## 12. Module Agrégation bancaire

### 12.1 Objectif

Récupérer automatiquement les comptes, soldes et transactions bancaires.

### 12.2 Fonctionnalités

- Connexion via fournisseur Open Banking.
- Import initial historique.
- Synchronisation périodique.
- Détection des doublons.
- Mise à jour des soldes.
- Gestion expiration consentement.
- Alerte avant expiration consentement.
- Import CSV manuel en secours.

### 12.3 Fréquence de synchronisation

```text
Soldes       : 1 à 2 fois par jour
Transactions : 1 fois par jour
Historique   : lors de la connexion initiale ou sur demande
```

### 12.4 Critères d’acceptation

- Le système importe au moins 90 jours d’historique bancaire.
- Les transactions importées ne sont pas dupliquées.
- Les soldes sont visibles par compte.
- Les virements internes peuvent être détectés.
- Une alerte apparaît avant expiration du consentement.

---

## 13. Module Catégorisation des dépenses

### 13.1 Objectif

Classer automatiquement les transactions selon des catégories réellement utiles à l’utilisateur.

### 13.2 Méthode

Ordre de priorité :

1. règle utilisateur exacte ;
2. règle système ;
3. historique des corrections ;
4. similarité avec anciennes transactions ;
5. suggestion IA ;
6. catégorie `Inconnu` si doute.

### 13.3 Score de confiance

```text
95-100 % : auto-validé
75-94 %  : accepté mais visible comme suggestion fiable
50-74 %  : à vérifier
0-49 %   : non classé
```

### 13.4 Apprentissage

Quand l’utilisateur corrige une catégorie, le système doit proposer :

- appliquer seulement à cette transaction ;
- appliquer aux transactions similaires futures ;
- appliquer aussi aux transactions similaires passées.

### 13.5 Exemples de règles

```text
Libellé contient "FULLI"             → Voiture / Péage
Libellé contient "UBER EATS"         → Restaurants / Livraison
Libellé contient "BINANCE"           → Investissement / Crypto
Libellé contient "ETORO"             → Investissement / Broker
Libellé contient "EDF"               → Logement / Électricité
Libellé contient "ASSURANCE" + auto  → Voiture / Assurance
Libellé contient "IMPOTS"            → Impôts / Fiscalité
```

---

## 14. Module Analyse budgétaire

### 14.1 Objectif

Fournir une lecture claire des habitudes de dépense.

### 14.2 Fonctionnalités

- Synthèse mensuelle automatique.
- Comparaison mois courant / mois précédent.
- Comparaison mois courant / moyenne 3, 6, 12 mois.
- Détection des dépenses fixes.
- Détection des dépenses variables.
- Détection des abonnements.
- Détection des hausses de prix.
- Reste à vivre prévisionnel.
- Taux d’épargne.
- Objectifs mensuels.
- Alertes de dérive.

### 14.3 Exemples d’insights

```text
- Tes dépenses voiture sont élevées ce mois-ci à cause de 3 pleins et 2 péages.
- Uber Eats est 42 % au-dessus de ta moyenne des 6 derniers mois.
- Ton abonnement logiciel a augmenté de 4,99 €.
- Ton taux d’épargne est de 18 %, objectif défini : 25 %.
- Les dépenses fixes représentent 54 % de tes revenus nets.
```

---

## 15. Module Emails et documents

### 15.1 Objectif

Transformer la boîte mail en source de données administratives exploitable.

### 15.2 Sources

- Gmail ;
- autres boîtes mail plus tard ;
- fichiers importés manuellement ;
- exports PDF ;
- photos de documents plus tard.

### 15.3 Classification email

Le système doit classifier les emails en :

```text
facture
reçu
avis administratif
impôts
assurance
banque
véhicule
abonnement
santé
publicité
spam / inutile
inconnu
```

### 15.4 Extraction depuis pièces jointes

Pour chaque PDF ou document détecté :

- télécharger la pièce jointe ;
- calculer un hash ;
- éviter les doublons ;
- extraire le texte ;
- identifier émetteur ;
- identifier date ;
- identifier montant ;
- identifier échéance ;
- identifier référence contrat/facture ;
- stocker le fichier ;
- associer à un email source.

### 15.5 OCR

Si le PDF ne contient pas de texte exploitable :

- lancer OCR ;
- stocker le texte OCR ;
- marquer le document comme `ocr_processed` ;
- attribuer un score de confiance inférieur.

---

## 16. Module Rapprochement facture / transaction

### 16.1 Objectif

Relier automatiquement les documents financiers aux mouvements bancaires.

### 16.2 Critères de rapprochement

Score basé sur :

- montant identique ;
- date proche ;
- fournisseur similaire ;
- libellé bancaire proche ;
- compte bancaire cohérent ;
- devise identique ;
- référence connue ;
- abonnement récurrent.

### 16.3 Score proposé

```text
+40 points : montant exact
+20 points : date à moins de 3 jours
+15 points : marchand similaire
+10 points : fournisseur déjà connu
+10 points : catégorie cohérente
+5 points  : référence ou contrat connu
```

### 16.4 Niveaux de confiance

```text
90-100 : rapprochement automatique
70-89  : rapprochement proposé à valider
40-69  : candidat faible
0-39   : non rapproché
```

### 16.5 Cas attendus

```text
Facture Fulli 42,80 € reçue par email
Transaction FULLI 42,80 € le lendemain
→ Lien automatique

Facture assurance 68,20 €
Transaction CREDIT MUTUEL ASSURANCE 68,20 €
→ Lien probable

Transaction Amazon 89,90 €
Aucune facture trouvée
→ Justificatif manquant
```

---

## 17. Module Contrats et abonnements

### 17.1 Objectif

Suivre les contrats, coûts, renouvellements et possibilités de résiliation.

### 17.2 Données suivies

- fournisseur ;
- type de contrat ;
- montant mensuel ou annuel ;
- date de début ;
- date de renouvellement ;
- délai de préavis ;
- mode de paiement ;
- document associé ;
- historique des hausses ;
- statut actif / résilié / à vérifier.

### 17.3 Détection automatique

Le système doit détecter :

- prélèvement récurrent ;
- facture mensuelle ;
- hausse de montant ;
- doublon d’abonnement ;
- abonnement inutilisé à vérifier manuellement.

### 17.4 Alertes

```text
- Renouvellement assurance habitation dans 45 jours.
- Abonnement logiciel augmenté de 20 %.
- Contrat sans document associé.
- Prélèvement récurrent non identifié.
```

---

## 18. Module Véhicules

### 18.1 Objectif

Centraliser les informations liées aux véhicules et éviter les oublis.

### 18.2 Données véhicule

- marque ;
- modèle ;
- année ;
- immatriculation masquée ;
- kilométrage ;
- assurance ;
- contrôle technique ;
- entretiens ;
- réparations ;
- factures ;
- dépenses carburant ;
- péages ;
- parking ;
- pneus ;
- échéances.

### 18.3 Contrôle technique

Le système doit permettre :

- saisie de la date limite actuelle ;
- import d’un PV de contrôle technique ;
- extraction de la date de validité ;
- création de rappels à J-90, J-60, J-30, J-15 et J-7 ;
- notification “prendre rendez-vous” ;
- statut : à jour / bientôt expiré / expiré / à vérifier.

### 18.4 Exemple d’alerte

```text
Contrôle technique BMW
Échéance : 13/05/2027
Action recommandée : prendre rendez-vous avant le 13/04/2027.
Priorité : warning à J-60, urgent à J-15.
```

### 18.5 Entretien préventif

Prévoir plus tard un module d’entretien :

- vidange ;
- filtres ;
- freins ;
- pneus ;
- liquide de frein ;
- contrôle batterie ;
- distribution / chaîne selon moteur ;
- notes mécaniques libres.

---

## 19. Module Patrimoine, crypto et brokers

### 19.1 Objectif

Afficher une vision consolidée du patrimoine.

### 19.2 Sources initiales

- Binance ;
- eToro ;
- comptes bancaires ;
- saisie manuelle pour actifs non connectés.

### 19.3 Données attendues

- actifs détenus ;
- quantité ;
- prix moyen si disponible ;
- valeur actuelle ;
- plus-value / moins-value latente ;
- devise ;
- répartition par classe d’actifs ;
- exposition crypto ;
- exposition actions ;
- cash disponible ;
- historique de valeur.

### 19.4 Restrictions

- lecture seule ;
- pas d’ordre automatique ;
- pas de levier automatique ;
- pas d’optimisation forcée ;
- conseils sous forme d’analyse, pas d’instruction d’investissement.

---

## 20. Module Assistant fiscal annuel

### 20.1 Objectif

Préparer un dossier annuel permettant de vérifier plus facilement la déclaration de revenus.

Le module doit aider à répondre à :

```text
Qu’est-ce que je dois vérifier avant de valider ma déclaration ?
Quels revenus et documents ai-je en ma possession ?
Quels montants semblent fiscalement pertinents ?
Quelles cases ou rubriques pourraient être concernées, à confirmer manuellement ?
Quels justificatifs dois-je conserver ?
```

### 20.2 Fonctionnalités V1

- créer un dossier fiscal par année ;
- regrouper les documents fiscaux ;
- repérer les emails impots.gouv ;
- repérer les avis d’impôt ;
- repérer les déclarations précédentes ;
- repérer les revenus connus sur comptes bancaires ;
- repérer les revenus d’employeur si documents disponibles ;
- repérer les intérêts bancaires si documents disponibles ;
- repérer les opérations crypto/broker à analyser ;
- générer une checklist ;
- générer une synthèse Markdown/PDF ;
- comparer les montants connus avec la déclaration préremplie saisie/importée manuellement.

### 20.3 Fonctionnalités V2

- préparation des frais réels si l’utilisateur les suit ;
- calcul indicatif kilométrique si données disponibles ;
- suivi dons ;
- suivi services à domicile ;
- suivi intérêts, dividendes, plus-values ;
- suivi plus-values crypto à partir d’exports ;
- détection des justificatifs manquants ;
- export d’un dossier fiscal complet.

### 20.4 Fonctionnalités explicitement interdites en automatique

- télédéclarer à la place de l’utilisateur ;
- certifier juridiquement les montants ;
- modifier les données impots.gouv ;
- contourner une authentification ;
- scraper massivement un portail administratif ;
- présenter une estimation comme une vérité fiscale.

### 20.5 Exemple de sortie attendue

```text
Dossier fiscal 2026 — revenus 2025

Documents trouvés :
- Avis d’impôt 2025
- Déclaration préremplie 2026 importée manuellement
- 2 documents bancaires fiscaux
- Export Binance 2025
- Export eToro 2025

Points à vérifier :
- Salaires préremplis : comparer avec bulletins / net imposable.
- Revenus mobiliers : vérifier documents eToro.
- Crypto : vérifier s’il existe des cessions imposables.
- Adresse : confirmer qu’elle est correcte.
- Dons / frais réels : aucune donnée fiable trouvée.

Statut : prêt pour vérification manuelle.
```

---

## 21. Module Notifications

### 21.1 Canaux possibles

- email ;
- Telegram ;
- notification navigateur ;
- webhook n8n ;
- Home Assistant plus tard ;
- digest quotidien ou hebdomadaire.

### 21.2 Types de notification

```text
urgent_action_required
upcoming_deadline
missing_document
unmatched_transaction
budget_drift
subscription_increase
consent_expiring
sync_error
fiscal_review_needed
vehicle_deadline
```

### 21.3 Politique de priorité

```text
critical : notification immédiate
urgent   : notification quotidienne jusqu’à action
warning  : digest quotidien
info     : digest hebdomadaire
```

### 21.4 Exemples

```text
URGENT — Contrôle technique expirant dans 15 jours.
WARNING — Consentement bancaire Crédit Mutuel à renouveler dans 10 jours.
INFO — 4 transactions ont été catégorisées avec faible confiance.
WARNING — Facture reçue mais aucune transaction correspondante trouvée.
```

---

## 22. Assistant conversationnel privé

### 22.1 Objectif

Permettre de poser des questions naturelles à sa vie administrative et financière.

### 22.2 Exemples de questions

```text
Combien j’ai dépensé en voiture ce mois-ci ?
Retrouve-moi la facture Fulli de juin.
Est-ce que j’ai payé mon assurance habitation ?
Quelles démarches arrivent dans les 60 prochains jours ?
Combien j’ai mis de côté cette année ?
Quelle est ma dépense Uber Eats moyenne ?
Qu’est-ce que je dois vérifier pour mes impôts ?
Quelle facture correspond à ce prélèvement ?
```

### 22.3 Règles de sécurité IA

- L’assistant doit citer ses sources internes : transaction, document, email, contrat.
- L’assistant doit dire quand il ne sait pas.
- L’assistant ne doit jamais inventer un montant.
- L’assistant doit distinguer fait, estimation et suggestion.
- Les actions sensibles nécessitent confirmation.

### 22.4 RAG documentaire

Une base vectorielle optionnelle permettra de rechercher dans :

- PDF ;
- factures ;
- contrats ;
- avis d’impôts ;
- emails importants ;
- notes utilisateur.

---

## 23. Workflows n8n recommandés

### 23.1 Workflow `bank-sync`

Déclenchement : cron quotidien.

Étapes :

```text
1. Vérifier connexions bancaires actives.
2. Appeler API Open Banking.
3. Importer comptes.
4. Importer soldes.
5. Importer transactions.
6. Dédupliquer.
7. Envoyer au backend.
8. Déclencher catégorisation.
9. Notifier erreurs si besoin.
```

### 23.2 Workflow `gmail-ingestion`

Déclenchement : toutes les 3 à 6 heures.

```text
1. Rechercher nouveaux emails pertinents.
2. Classifier sujet / expéditeur.
3. Télécharger pièces jointes.
4. Envoyer PDF au backend.
5. Lancer extraction.
6. Créer document.
7. Déclencher rapprochement transaction.
```

### 23.3 Workflow `subscription-monitor`

Déclenchement : hebdomadaire.

```text
1. Identifier transactions récurrentes.
2. Détecter nouveaux abonnements.
3. Détecter variations de prix.
4. Mettre à jour contrats.
5. Créer alertes si hausse ou inconnue.
```

### 23.4 Workflow `vehicle-reminders`

Déclenchement : quotidien.

```text
1. Charger véhicules.
2. Vérifier contrôle technique.
3. Vérifier assurance.
4. Vérifier événements d’entretien.
5. Créer rappels ou notifications.
```

### 23.5 Workflow `fiscal-year-prep`

Déclenchement : mensuel, puis renforcé entre avril et juin.

```text
1. Chercher documents fiscaux.
2. Chercher emails impots.gouv.
3. Chercher documents broker/crypto.
4. Chercher revenus entrants significatifs.
5. Générer checklist.
6. Notifier si action nécessaire.
```

---

## 24. API interne minimale

### 24.1 Auth

```text
POST /auth/login
POST /auth/logout
POST /auth/refresh
GET  /auth/me
```

### 24.2 Comptes

```text
GET /accounts
GET /accounts/:id
POST /accounts/manual
PATCH /accounts/:id
```

### 24.3 Transactions

```text
GET /transactions
GET /transactions/:id
PATCH /transactions/:id/category
POST /transactions/import
POST /transactions/:id/link-document
```

### 24.4 Documents

```text
GET /documents
GET /documents/:id
POST /documents/upload
POST /documents/:id/extract
POST /documents/:id/link-transaction
PATCH /documents/:id
```

### 24.5 Contrats

```text
GET /contracts
POST /contracts
GET /contracts/:id
PATCH /contracts/:id
```

### 24.6 Véhicules

```text
GET /vehicles
POST /vehicles
GET /vehicles/:id
PATCH /vehicles/:id
POST /vehicles/:id/events
```

### 24.7 Patrimoine

```text
GET /assets
GET /assets/summary
POST /assets/sync
```

### 24.8 Rappels

```text
GET /reminders
POST /reminders
PATCH /reminders/:id
POST /reminders/:id/complete
```

### 24.9 Assistant

```text
POST /assistant/query
POST /assistant/action-preview
POST /assistant/action-confirm
```

---

## 25. Interface utilisateur

### 25.1 Pages principales

```text
/dashboard
/accounts
/transactions
/documents
/contracts
/vehicles
/assets
/budget
/goals
/tax
/reminders
/assistant
/settings
```

### 25.2 Dashboard

Cartes :

- patrimoine total ;
- solde courant ;
- dépenses du mois ;
- revenus du mois ;
- taux d’épargne ;
- alertes ;
- prochaines échéances ;
- documents à traiter ;
- transactions à vérifier.

### 25.3 Page Transactions

Fonctions :

- recherche ;
- filtres par compte, date, catégorie, montant ;
- édition catégorie ;
- split transaction ;
- rattachement document ;
- création règle depuis transaction ;
- export CSV.

### 25.4 Page Documents

Fonctions :

- liste documents ;
- aperçu PDF ;
- recherche texte ;
- statut extraction ;
- document lié à transaction ;
- tags ;
- téléchargement ;
- archivage.

### 25.5 Page Fiscalité

Fonctions :

- année fiscale ;
- documents fiscaux ;
- revenus connus ;
- points à vérifier ;
- export dossier ;
- checklist ;
- statut prêt / incomplet.

### 25.6 Page Assistant

Interface conversationnelle avec sources.

Exemple :

```text
Utilisateur : Retrouve la facture liée au prélèvement Fulli de 42,80 €.
Assistant : J’ai trouvé une facture Fulli du 03/07/2026 de 42,80 €, reçue par email le 04/07/2026. Elle correspond au prélèvement du 05/07/2026 avec un score de 96 %.
```

---

## 26. Sécurité

### 26.1 Principes

- chiffrement des secrets ;
- accès dashboard protégé ;
- MFA si possible ;
- APIs en lecture seule ;
- sauvegardes chiffrées ;
- pas de secrets dans Git ;
- pas de logs sensibles ;
- fichiers privés ;
- audit trail ;
- permissions minimales.

### 26.2 Secrets

Les secrets doivent être stockés dans :

- variables d’environnement ;
- gestionnaire de secrets ;
- coffre externe compatible ;
- credentials n8n correctement chiffrés.

Le fichier `.env.example` doit exister, mais jamais le `.env` réel.

### 26.3 n8n

En self-hosted, définir une clé d’encryption stable pour n8n afin d’éviter la perte d’accès aux credentials après migration ou redéploiement.

### 26.4 Accès public

Par défaut, ne pas exposer l’application directement sur Internet.

Options recommandées :

```text
- VPN type Tailscale / WireGuard
- reverse proxy avec HTTPS
- authentification forte
- IP allowlist si possible
```

### 26.5 Sauvegardes

Minimum :

```text
Base PostgreSQL : quotidienne
Documents       : quotidienne
Config n8n      : hebdomadaire
.env/secrets    : sauvegarde manuelle chiffrée
Test restore    : mensuel
```

---

## 27. Stratégie IA

### 27.1 Usage autorisé

- classification de transactions ambiguës ;
- résumé de documents ;
- extraction d’informations ;
- génération de synthèses ;
- assistant conversationnel ;
- détection de points à vérifier.

### 27.2 Usage interdit

- inventer des montants ;
- décider d’un investissement ;
- envoyer une démarche administrative ;
- masquer une incertitude ;
- modifier des données sans trace.

### 27.3 Mode de réponse IA

Chaque réponse doit distinguer :

```text
Fait vérifié
Estimation
Hypothèse
Action recommandée
Action requise
```

### 27.4 Exemple

```text
Fait vérifié : une facture Fulli de 42,80 € a été trouvée.
Fait vérifié : une transaction bancaire de 42,80 € existe 2 jours après.
Estimation : il s’agit probablement du même événement.
Confiance : 96 %.
Action : aucune validation requise sauf si tu veux corriger.
```

---

## 28. Roadmap

### 28.1 Phase 0 — Socle technique

Objectif : poser les fondations.

Tâches :

- créer repo ;
- ajouter Docker Compose ;
- créer API backend ;
- créer frontend minimal ;
- créer base PostgreSQL ;
- créer migrations ;
- créer authentification ;
- créer système de logs ;
- créer sauvegarde de base.

Critère de fin :

```text
L’utilisateur peut se connecter et voir un dashboard vide sans erreur.
```

### 28.2 Phase 1 — Transactions bancaires

Objectif : remplacer le suivi Excel minimal.

Tâches :

- connecter fournisseur Open Banking ;
- importer comptes ;
- importer transactions ;
- afficher transactions ;
- catégoriser par règles ;
- corriger manuellement ;
- générer synthèse mensuelle.

Critère de fin :

```text
L’utilisateur peut consulter ses transactions et obtenir une synthèse mensuelle fiable.
```

### 28.3 Phase 2 — Emails et factures

Objectif : récupérer les justificatifs.

Tâches :

- connecter Gmail ;
- filtrer emails utiles ;
- télécharger pièces jointes ;
- extraire texte PDF ;
- créer documents ;
- afficher documents ;
- rechercher documents.

Critère de fin :

```text
Les factures reçues par email sont automatiquement classées et visibles.
```

### 28.4 Phase 3 — Rapprochement automatique

Objectif : relier paiement et facture.

Tâches :

- créer algorithme de matching ;
- calculer score ;
- lier automatiquement si confiance élevée ;
- proposer validation si confiance moyenne ;
- afficher transactions sans justificatif.

Critère de fin :

```text
Une facture courante peut être liée automatiquement à sa transaction bancaire.
```

### 28.5 Phase 4 — Contrats, abonnements, rappels

Objectif : gérer les échéances.

Tâches :

- créer contrats ;
- détecter récurrences ;
- créer rappels ;
- notifier échéances ;
- détecter hausses d’abonnements.

Critère de fin :

```text
Le système notifie les échéances utiles et les hausses de prélèvement.
```

### 28.6 Phase 5 — Véhicule

Objectif : suivre contrôle technique et entretien.

Tâches :

- créer fiche véhicule ;
- saisir/importer date contrôle technique ;
- créer rappels ;
- lier dépenses voiture ;
- lier factures garage, péage, assurance.

Critère de fin :

```text
Le système sait quand le contrôle technique approche et notifie de prendre rendez-vous.
```

### 28.7 Phase 6 — Patrimoine

Objectif : consolider crypto, actions et cash.

Tâches :

- connecter Binance en lecture seule ;
- connecter eToro en lecture seule ;
- récupérer positions ;
- afficher allocation ;
- calculer patrimoine total ;
- suivre historique.

Critère de fin :

```text
Le dashboard affiche une estimation consolidée du patrimoine.
```

### 28.8 Phase 7 — Assistant fiscal

Objectif : préparer la déclaration annuelle.

Tâches :

- créer dossier fiscal par année ;
- classifier documents fiscaux ;
- détecter revenus entrants ;
- intégrer exports brokers/crypto ;
- générer checklist ;
- générer synthèse Markdown/PDF ;
- comparer avec déclaration préremplie importée manuellement.

Critère de fin :

```text
Le système génère un dossier fiscal annuel exploitable pour vérification manuelle.
```

### 28.9 Phase 8 — Assistant conversationnel

Objectif : interroger sa vie administrative en langage naturel.

Tâches :

- créer endpoint assistant ;
- connecter données structurées ;
- connecter documents ;
- citer les sources internes ;
- ajouter confirmations d’action ;
- ajouter historique.

Critère de fin :

```text
L’utilisateur peut poser une question et obtenir une réponse sourcée depuis ses données.
```

---

## 29. MVP recommandé

### 29.1 MVP réaliste

Le MVP doit volontairement être limité à :

```text
- Connexion bancaire ou import CSV bancaire
- Transactions
- Catégorisation
- Dashboard mensuel
- Gmail factures
- Documents PDF
- Rapprochement simple
- Rappels manuels
```

### 29.2 Pourquoi ce MVP

C’est la partie qui remplace immédiatement le tableur manuel et donne une valeur concrète.

Le reste peut venir ensuite.

---

## 30. Critères de réussite globaux

Le projet est réussi si :

- l’utilisateur n’a plus besoin de maintenir son Excel mensuel ;
- les dépenses sont catégorisées correctement à plus de 90 % après apprentissage ;
- les factures principales sont automatiquement retrouvées ;
- les transactions importantes ont un justificatif lié ;
- les échéances administratives importantes sont notifiées ;
- le patrimoine global est consultable en moins de 30 secondes ;
- le dossier fiscal annuel est préparé avant la période déclarative ;
- les données restent privées et sauvegardées ;
- l’utilisateur comprend pourquoi l’assistant propose une action.

---

## 31. Tests à prévoir

### 31.1 Tests unitaires

- parsing transaction ;
- catégorisation ;
- matching facture/transaction ;
- extraction date/montant ;
- calcul budget ;
- génération rappel.

### 31.2 Tests d’intégration

- import bancaire complet ;
- import email avec PDF ;
- création document ;
- rapprochement ;
- affichage dashboard.

### 31.3 Tests de sécurité

- absence de secrets dans logs ;
- accès non authentifié impossible ;
- fichiers non publics ;
- backup restaurable ;
- permissions API limitées.

### 31.4 Jeux de données fictifs

Créer des fixtures :

```text
- transactions Crédit Mutuel fictives
- factures Fulli fictives
- factures Uber Eats fictives
- assurance fictive
- contrôle technique fictif
- export Binance fictif
- export eToro fictif
```

---

## 32. Exemple de `.env.example`

```env
APP_ENV=development
APP_URL=http://localhost:3000
API_URL=http://localhost:8000

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=lifepilot
POSTGRES_USER=lifepilot
POSTGRES_PASSWORD=change_me

JWT_SECRET=change_me
ENCRYPTION_KEY=change_me_32_bytes_minimum

N8N_ENCRYPTION_KEY=change_me_stable_key
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=change_me

GOCARDLESS_SECRET_ID=
GOCARDLESS_SECRET_KEY=

GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=

BINANCE_API_KEY=
BINANCE_API_SECRET=

ETORO_API_KEY=
ETORO_API_SECRET=

MINIO_ROOT_USER=lifepilot
MINIO_ROOT_PASSWORD=change_me
MINIO_BUCKET=documents

QDRANT_URL=http://qdrant:6333
LLM_PROVIDER=none
LLM_API_KEY=
```

---

## 33. Exemple de `docker-compose.yml` cible

```yaml
services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: lifepilot
      POSTGRES_USER: lifepilot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    restart: unless-stopped

  minio:
    image: minio/minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data

  n8n:
    image: n8nio/n8n:latest
    restart: unless-stopped
    environment:
      N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY}
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_DATABASE: lifepilot
      DB_POSTGRESDB_USER: lifepilot
      DB_POSTGRESDB_PASSWORD: ${POSTGRES_PASSWORD}
    depends_on:
      - postgres
    volumes:
      - n8n_data:/home/node/.n8n

  api:
    build: ./apps/api
    restart: unless-stopped
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minio

  web:
    build: ./apps/web
    restart: unless-stopped
    env_file: .env
    depends_on:
      - api

volumes:
  postgres_data:
  minio_data:
  n8n_data:
```

---

## 34. Sources et références utiles

- GoCardless Bank Account Data — accès comptes, soldes, transactions, historique et consentement : https://developer.gocardless.com/bank-account-data/overview
- Documentation GoCardless — accord utilisateur et période d’accès : https://developer.gocardless.com/bank-account-data/quick-start-guide/
- FranceConnect — dispositif d’identification et services accessibles : https://www.franceconnect.gouv.fr/
- FranceConnect — services accessibles, dont impots.gouv et France Titres / ANTS : https://www.franceconnect.gouv.fr/services-accessibles/
- API Impôt particulier — accès réservé à des entités éligibles dans un cadre réglementaire : https://www.data.gouv.fr/dataservices/api-impot-particulier
- API Particulier — bouquet d’API pour agents publics : https://particulier.api.gouv.fr/
- Impots.gouv — déclaration automatique : https://www.impots.gouv.fr/la-declaration-automatique-0
- Impots.gouv — dates limites de déclaration 2026 : https://www.impots.gouv.fr/toutes-les-questions/particulier/quelle-date-dois-je-faire-ma-declaration
- Service-Public — contrôle technique voiture catégorie M1 : https://www.service-public.fr/particuliers/vosdroits/F2878
- n8n — clé d’encryption self-hosted : https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key
- n8n — secret stores externes : https://docs.n8n.io/administer/manage-credentials/use-external-secret-stores

---

## 35. Décisions de conception à prendre

### 35.1 Backend

Choisir entre :

```text
FastAPI Python
ou
NestJS TypeScript
```

Recommandation : **FastAPI** si priorité extraction PDF, data, IA, fiscalité et parsing.  
Recommandation : **NestJS** si priorité architecture TypeScript homogène avec frontend.

### 35.2 Finance engine

Choisir entre :

```text
Moteur maison
ou
Intégration partielle Firefly III
```

Recommandation : démarrer moteur maison léger, mais étudier Firefly III pour éviter de recréer inutilement budgets, règles et comptes si le besoin devient plus comptable.

### 35.3 IA

Choisir entre :

```text
IA cloud
IA locale
mode hybride
```

Recommandation : mode hybride avec anonymisation maximale pour les données sensibles.

### 35.4 Stockage documents

Choisir entre :

```text
MinIO
filesystem chiffré
S3 compatible
```

Recommandation : MinIO si déploiement Docker propre ; filesystem chiffré si simplicité maximale.

---

## 36. Première liste d’issues GitHub

```text
[INIT] Créer repo et structure monorepo
[INIT] Ajouter Docker Compose initial
[DB] Créer schéma PostgreSQL initial
[API] Ajouter authentification locale
[WEB] Créer layout dashboard
[FINANCE] Créer modèle accounts
[FINANCE] Créer modèle transactions
[FINANCE] Import CSV bancaire
[FINANCE] Catégorisation par règles simples
[FINANCE] Synthèse mensuelle
[DOCS] Connexion Gmail n8n
[DOCS] Ingestion pièces jointes PDF
[DOCS] Extraction texte PDF
[MATCHING] Algorithme facture/transaction V1
[REMINDERS] Modèle rappels
[VEHICLE] Fiche véhicule V1
[SECURITY] Mettre en place gestion secrets
[BACKUP] Script sauvegarde PostgreSQL
[TESTS] Fixtures transactions/documents fictifs
```

---

## 37. Définition de “terminé” pour la V1

La V1 est terminée quand :

- l’application se lance via Docker Compose ;
- l’utilisateur peut se connecter ;
- des transactions peuvent être importées ;
- les transactions sont catégorisées ;
- les catégories peuvent être corrigées ;
- une synthèse mensuelle est générée ;
- des PDF de factures peuvent être importés depuis Gmail ou manuellement ;
- une facture peut être rapprochée d’une transaction ;
- un rappel peut être créé ;
- un rappel peut générer une notification ;
- les données sont sauvegardables et restaurables.

---

## 38. Philosophie finale

LifePilot Admin ne doit pas être une application de plus à consulter.

Il doit devenir le système qui répond à trois questions :

```text
Qu’est-ce qui s’est passé ?
Qu’est-ce que ça veut dire ?
Qu’est-ce que je dois faire ?
```

Le reste, c’est de la décoration numérique. Et l’humanité en a déjà produit assez.
