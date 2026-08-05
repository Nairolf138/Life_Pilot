# Workflows n8n

Ce document décrit les workflows n8n Life Pilot. n8n orchestre les déclenchements, intégrations externes et notifications ; l'API backend reste la source de vérité pour les règles métier, l'idempotence et la persistance.

## Variables et principes communs

| Élément | Règle commune |
| --- | --- |
| Secret interne | Tous les endpoints `/internal/n8n/*` sont appelés avec `X-N8N-Secret: {{$env.LIFEPILOT_N8N_SECRET}}`. La même valeur doit être configurée côté API dans `N8N_INTERNAL_SECRET`. |
| URL backend | `LIFEPILOT_API_URL` contient l'URL de base de l'API, sans slash final. |
| Utilisateur cible | Les workflows mono-utilisateur utilisent `LIFEPILOT_USER_ID`. Les workflows multi-utilisateurs doivent itérer sur une liste backend ou une variable dédiée et ne jamais deviner l'utilisateur depuis des données externes. |
| Idempotence | Chaque écriture doit porter une clé stable (`idempotency_key`, `external_id`, `deduplication_key`, période fiscale, identifiant Gmail ou identifiant de récurrence). |
| Logs | Les nœuds de journalisation n8n doivent émettre un objet JSON avec `workflow`, `step`, `message`, `user_id` si disponible et `at`. En production, relayer ces logs vers l'observabilité ou une alerte opérée. |

## `bank-sync`

### Déclencheur

- Déclenchement planifié toutes les 6 heures pour les comptes actifs.
- Déclenchement manuel possible après ajout d'un compte bancaire ou renouvellement de consentement Open Banking.
- Option recommandée : exécuter une synchronisation complète de rattrapage une fois par nuit et des synchronisations incrémentales en journée.

### Entrées

- `LIFEPILOT_API_URL` : URL de base de l'API.
- `LIFEPILOT_N8N_SECRET` : secret interne n8n.
- `LIFEPILOT_USER_ID` ou liste d'utilisateurs à synchroniser.
- Identifiants de comptes à synchroniser, si le backend ne les résout pas automatiquement.
- Fenêtre temporelle : `from_date`, `to_date`, `lookback_days` ou curseur de synchronisation.
- Réponse du connecteur bancaire : comptes, soldes, transactions, statut du consentement, curseur de pagination.

### Étapes

1. Charger les comptes bancaires synchronisables pour l'utilisateur ou le lot d'utilisateurs.
2. Vérifier que chaque compte dispose d'un consentement valide et non expiré.
3. Appeler le fournisseur Open Banking avec le curseur ou la fenêtre de dates.
4. Normaliser les comptes, soldes et transactions : devise, libellé brut, libellé nettoyé, date de valeur, montant signé, identifiant externe.
5. Envoyer les transactions au backend par lots idempotents.
6. Déclencher la catégorisation, la détection de virements internes et la détection de récurrences.
7. Mettre à jour le curseur de synchronisation et le statut du consentement.
8. Journaliser le nombre de comptes et transactions importés, ignorés ou en erreur.

### Endpoints backend appelés

```http
GET /internal/n8n/bank/accounts?user_id=<uuid>&syncable=true
X-N8N-Secret: <secret partagé>
```

```http
POST /internal/n8n/bank/transactions/import
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/bank/sync-state
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/recurrences/analyze
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

### Credentials nécessaires

- Credential n8n du fournisseur bancaire ou Open Banking : OAuth2, API key ou certificat selon l'agrégateur.
- `LIFEPILOT_N8N_SECRET` pour les endpoints internes.
- Secret ou token de chiffrement du connecteur si le fournisseur impose une signature des requêtes.
- Accès réseau sortant de n8n vers l'API Life Pilot et le fournisseur bancaire.

### Erreurs possibles

- Consentement expiré, révoqué ou nécessitant une authentification forte.
- Limite de débit du fournisseur bancaire.
- Pagination incomplète ou curseur invalide.
- Transaction sans identifiant externe stable.
- Échec de validation backend : devise inconnue, compte non trouvé, utilisateur non autorisé.
- Erreur temporaire API, réseau ou base de données.

### Stratégie de retry

- Réessayer les erreurs réseau, `429`, `502`, `503` et `504` avec backoff exponentiel : 1 min, 5 min, 15 min, puis prochaine planification.
- Ne pas réessayer automatiquement les erreurs `401`, `403` ou consentement expiré ; créer une notification de reconnexion bancaire.
- Réimporter les lots avec les mêmes identifiants externes et la même clé d'idempotence pour permettre un upsert sans doublon.
- Après échec partiel, reprendre au dernier curseur confirmé par le backend, jamais au curseur reçu mais non persisté.

### Règles de sécurité

- Ne jamais stocker de token bancaire dans des nœuds Code ou dans le payload backend ; utiliser les credentials chiffrés n8n.
- Masquer les IBAN, numéros de compte et libellés sensibles dans les logs.
- Vérifier que `user_id` et comptes retournés appartiennent au même tenant.
- Transmettre uniquement les champs nécessaires au backend ; éviter de conserver les réponses brutes du fournisseur hors stockage sécurisé.
- Rotation régulière des secrets Open Banking et du secret interne n8n.

## `gmail-ingestion`

### Déclencheur

- Le workflow `workflows/n8n/gmail-ingestion.json` est planifié toutes les 4 heures.
- La requête Gmail cible les PDF récents : `newer_than:7d has:attachment filename:pdf (facture OR invoice OR reçu OR receipt OR contrat OR échéance)`.

### Entrées

- Messages Gmail avec métadonnées (`id`, `subject`, `from`, pièces jointes).
- Pièces jointes PDF téléchargées dans la propriété binaire `document`.
- `LIFEPILOT_API_URL`, `LIFEPILOT_N8N_SECRET`, `LIFEPILOT_USER_ID`.
- Classification simple déduite du sujet et de l'expéditeur : `invoice`, `receipt`, `contract`, `notice` ou `email_pdf`.

### Étapes

1. Rechercher les emails pertinents avec pièces jointes PDF.
2. Classifier le sujet et l'expéditeur pour produire `document_type` et `title`.
3. Ignorer les emails sans PDF.
4. Télécharger chaque PDF détecté.
5. Envoyer le PDF au backend en `multipart/form-data`.
6. Laisser le backend stocker le document, détecter les doublons et déclencher l'extraction texte.
7. Journaliser les erreurs par email et par pièce jointe.

### Endpoints backend appelés

```http
POST /internal/n8n/documents
X-N8N-Secret: <secret partagé>
Content-Type: multipart/form-data
```

Champs : `file`, `user_id`, `document_type`, `title`.

### Credentials nécessaires

- Credential n8n **Gmail OAuth2** nommé `Gmail Life Pilot`.
- Scopes recommandés : `https://www.googleapis.com/auth/gmail.readonly` et `https://www.googleapis.com/auth/gmail.metadata`.
- `LIFEPILOT_N8N_SECRET` pour l'appel backend.

### Erreurs possibles

- OAuth Gmail expiré ou révoqué.
- Quota Gmail dépassé.
- Pièce jointe absente, non PDF ou trop volumineuse.
- Téléchargement binaire incomplet.
- Secret n8n invalide, backend indisponible ou extraction OCR en échec.
- Document déjà importé.

### Stratégie de retry

- Les nœuds de téléchargement et d'envoi utilisent `continueOnFail` pour journaliser sans bloquer tout le lot.
- Réessayer automatiquement les erreurs réseau et `5xx` avec backoff court.
- Ne pas réessayer les pièces jointes non PDF ou les erreurs d'autorisation sans action utilisateur.
- Le backend doit dédupliquer par hash de fichier, identifiant Gmail ou métadonnées stables afin que les retries restent sûrs.

### Règles de sécurité

- Utiliser un accès Gmail en lecture seule ; ne pas supprimer ni modifier les emails.
- Ne pas loguer le contenu des emails ni les PDF, uniquement les identifiants techniques et messages d'erreur résumés.
- Refuser les fichiers non PDF et appliquer une limite de taille côté backend.
- Vérifier le secret interne et l'appartenance du document à `LIFEPILOT_USER_ID`.

## `subscription-monitor`

### Déclencheur

- Le workflow `workflows/n8n/subscription-monitor.json` s'exécute chaque lundi à 06:00.
- Il peut être relancé manuellement après une importation bancaire massive.

### Entrées

- `LIFEPILOT_USER_ID`.
- `LIFEPILOT_SUBSCRIPTION_LOOKBACK_DAYS`, valeur par défaut `400`.
- `LIFEPILOT_SUBSCRIPTION_ANALYSIS_MODE`, valeur par défaut `launch_or_get`.
- Rapport backend de récurrences : détections, alertes, contrat suggéré, transactions sources.

### Étapes

1. Appeler l'analyse des récurrences avec une clé `subscription-monitor:<date ISO>`.
2. Normaliser les détections depuis `report`, `analysis`, `data` ou un tableau direct.
3. Identifier les nouveaux abonnements sans contrat rattaché.
4. Identifier les variations de prix et alertes associées.
5. Créer ou mettre à jour les contrats en statut `to_review`.
6. Créer les rappels ou notifications de validation.
7. Journaliser le résultat de chaque écriture.

### Endpoints backend appelés

```http
POST /internal/n8n/recurrences/analyze
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/contracts/upsert-from-recurrence
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/subscription-monitor/reminders
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

### Credentials nécessaires

- `LIFEPILOT_N8N_SECRET` pour les endpoints internes.
- Accès aux variables `LIFEPILOT_API_URL`, `LIFEPILOT_USER_ID` et paramètres de lookback.
- Aucun credential bancaire direct si les transactions sont déjà importées par `bank-sync`.

### Erreurs possibles

- Aucune transaction disponible ou historique insuffisant.
- Analyse déjà en cours pour la même clé d'idempotence.
- Détection sans marchand, montant ou période exploitable.
- Conflit avec un contrat existant rattaché manuellement.
- Échec de création des rappels ou contrat déjà fermé.

### Stratégie de retry

- Réessayer les erreurs temporaires du backend avec la même clé `subscription-monitor:<date ISO>`.
- Laisser le backend retourner un résultat existant en mode `launch_or_get` plutôt que créer une analyse concurrente.
- Ne pas créer de rappel en doublon : utiliser la clé de récurrence et le type d'alerte comme clé de déduplication.
- Isoler les erreurs par détection pour continuer à traiter les autres abonnements.

### Règles de sécurité

- Ne pas exposer les libellés bancaires complets dans les notifications externes ; préférer marchand, montant et période.
- Les contrats créés automatiquement restent `to_review` jusqu'à validation utilisateur.
- Ne jamais supprimer ou résilier un contrat depuis n8n.
- Restreindre les endpoints à `X-N8N-Secret` et contrôler l'appartenance de chaque transaction à l'utilisateur.

## `vehicle-reminders`

### Déclencheur

- Le workflow `workflows/n8n/vehicle-reminders.json` s'exécute tous les jours à 07:30.
- L'horaire peut être positionné avant `notifications` pour inclure les nouveaux rappels dans le digest quotidien.

### Entrées

- `LIFEPILOT_USER_ID`.
- `LIFEPILOT_VEHICLE_LOOKAHEAD_DAYS`, valeur par défaut `90`.
- `LIFEPILOT_VEHICLE_REMINDER_LEAD_DAYS`, valeur par défaut `30`.
- `LIFEPILOT_VEHICLE_MILEAGE_LOOKAHEAD`, valeur par défaut `1500`.
- Véhicules, contrat d'assurance rattaché et événements d'entretien.
- Canal de notification optionnel : `LIFEPILOT_NOTIFICATION_CHANNEL_URL`, `LIFEPILOT_NOTIFICATION_CHANNEL_AUTH`.

### Étapes

1. Charger les véhicules avec événements et fenêtre de projection.
2. Vérifier `technical_inspection_due_date`.
3. Vérifier les échéances d'assurance depuis le véhicule ou le contrat associé.
4. Vérifier les entretiens par date ou kilométrage.
5. Générer des rappels normalisés avec `deduplication_key` stable.
6. Upserter les rappels dans le backend.
7. Notifier le canal configuré uniquement si une action est requise.
8. Journaliser chargement, upsert et notification.

### Endpoints backend appelés

```http
GET /internal/n8n/vehicles?user_id=<uuid>&include_events=true&lookahead_days=90
X-N8N-Secret: <secret partagé>
```

```http
POST /internal/n8n/vehicle-reminders/upsert
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST <LIFEPILOT_NOTIFICATION_CHANNEL_URL>
Authorization: <optionnel>
Content-Type: application/json
```

### Credentials nécessaires

- `LIFEPILOT_N8N_SECRET` pour l'API interne.
- Token ou secret du canal de notification si une notification externe est utilisée.
- Aucun credential constructeur ou assurance n'est requis si les données véhicule sont déjà dans Life Pilot.

### Erreurs possibles

- Véhicule sans date d'échéance exploitable.
- Date invalide ou kilométrage manquant.
- Contrat d'assurance non rattaché ou supprimé.
- Upsert backend en échec.
- Canal de notification indisponible.

### Stratégie de retry

- Réessayer le chargement et l'upsert sur erreurs temporaires.
- Ne pas dupliquer les rappels grâce à `deduplication_key`.
- Ne pas rouvrir automatiquement un rappel terminé ou ignoré sauf si l'échéance change.
- Si la notification échoue après upsert, laisser le workflow `notifications` prendre le relais lors de son prochain passage.

### Règles de sécurité

- Masquer l'immatriculation dans les logs et notifications, par exemple `AB-***-CD`.
- Ne pas exposer d'adresse, certificat d'assurance ou document véhicule dans le canal externe.
- Contrôler que les véhicules chargés appartiennent à `LIFEPILOT_USER_ID`.
- Limiter les notifications externes au minimum actionnable : type d'échéance, date, sévérité.

## `fiscal-year-prep`

### Déclencheur

- Déclenchement planifié annuel, recommandé le 1er janvier et un rappel mensuel jusqu'à clôture de l'année fiscale.
- Déclenchement manuel possible depuis l'administration ou le tableau de bord fiscal.
- Déclenchement complémentaire après import massif de documents ou transactions de l'année concernée.

### Entrées

- `LIFEPILOT_USER_ID`.
- Année fiscale cible : `tax_year` ou `LIFEPILOT_TAX_YEAR`.
- Pays ou régime fiscal si nécessaire : `country`, `tax_profile_id`.
- Transactions de l'année, documents rattachés, contrats, revenus, dépenses déductibles, justificatifs manquants.
- Paramètres de notification pour relancer l'utilisateur si des pièces sont manquantes.

### Étapes

1. Créer ou récupérer le dossier fiscal de l'année cible.
2. Lancer l'analyse des transactions et documents de l'année.
3. Classer les revenus, dépenses récurrentes, frais, dons, intérêts, dividendes et documents administratifs.
4. Comparer les exigences documentaires aux justificatifs déjà présents.
5. Créer une checklist de pièces manquantes et tâches utilisateur.
6. Préparer un résumé fiscal et un export de travail.
7. Notifier l'utilisateur uniquement si des actions sont requises.
8. Marquer le dossier comme `preparing`, `ready_for_review` ou `missing_documents` selon le résultat backend.

### Endpoints backend appelés

```http
POST /internal/n8n/tax-year-files/upsert
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/tax-year-files/analyze
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/tax-year-files/document-requirements
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST /internal/n8n/tax-year-files/notifications
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

### Credentials nécessaires

- `LIFEPILOT_N8N_SECRET` pour les endpoints internes.
- Accès au canal de notification si les relances sortent de Life Pilot.
- Aucun credential fiscal externe par défaut ; toute connexion à un portail fiscal doit utiliser OAuth ou coffre de secrets n8n, jamais des identifiants en clair.

### Erreurs possibles

- Année fiscale absente ou incohérente avec les dates de transactions.
- Documents manquants ou non extraits par OCR.
- Catégorie fiscale ambiguë nécessitant une validation utilisateur.
- Export fiscal impossible car le dossier est incomplet.
- Incohérence entre transactions et justificatifs rattachés.

### Stratégie de retry

- Utiliser une clé d'idempotence `fiscal-year-prep:<user_id>:<tax_year>`.
- Réessayer les analyses et exports sur erreurs temporaires.
- Ne pas recréer les tâches existantes ; upsert par `tax_year`, `requirement_code` et `document_type`.
- En cas de documents non extraits, relancer l'OCR une fois puis classer en action utilisateur si l'échec persiste.

### Règles de sécurité

- Les données fiscales sont hautement sensibles : ne jamais les loguer en clair.
- Restreindre les exports à des emplacements chiffrés et à durée de vie limitée.
- Ne pas envoyer de montants détaillés ou documents dans des canaux externes non chiffrés.
- Exiger une validation utilisateur avant toute déclaration, suppression ou transmission à un tiers.

## `notifications`

### Déclencheur

- Le workflow `workflows/n8n/notifications.json` s'exécute tous les jours à 08:00.
- Il peut être déclenché manuellement après création en masse de rappels.

### Entrées

- `LIFEPILOT_NOTIFICATIONS_LIMIT`, valeur par défaut `100`.
- Notifications candidates retournées par le backend, sous forme de tableau direct ou enveloppées dans `candidates`, `notifications` ou `data`.
- Priorités `critical`, `urgent`, `warning`, `info`.
- Canal cible : `LIFEPILOT_NOTIFICATION_CHANNEL`, `LIFEPILOT_NOTIFICATION_CHANNEL_URL`, `LIFEPILOT_NOTIFICATION_CHANNEL_AUTH`.

### Étapes

1. Récupérer les notifications candidates avec `mark_as_sent=false`.
2. Journaliser et arrêter la branche en cas d'erreur de récupération.
3. Regrouper les notifications par priorité et trier les groupes.
4. Envoyer chaque groupe vers le canal configuré.
5. Si le canal accepte le groupe, marquer uniquement ces notifications comme envoyées.
6. Journaliser séparément les erreurs de canal et les succès.

### Endpoints backend appelés

```http
GET /internal/n8n/notifications/candidates?limit=100&mark_as_sent=false
X-N8N-Secret: <secret partagé>
```

```http
POST /internal/n8n/notifications/mark-sent
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

```http
POST <LIFEPILOT_NOTIFICATION_CHANNEL_URL>
Authorization: <optionnel>
Content-Type: application/json
```

### Credentials nécessaires

- `LIFEPILOT_N8N_SECRET` pour récupérer et marquer les notifications.
- Credential ou token du canal de notification : email, Telegram, WhatsApp, webhook ou service interne.
- `LIFEPILOT_NOTIFICATION_CHANNEL_AUTH` si le canal exige un header `Authorization`.

### Erreurs possibles

- Backend indisponible ou secret invalide.
- Payload sans `id` ni `reminder_id`, impossible à marquer comme envoyé.
- Canal externe indisponible, timeout, limite de débit ou rejet applicatif.
- Notification trop volumineuse pour le canal.
- Échec partiel sur un groupe de priorité.

### Stratégie de retry

- Ne jamais appeler `mark-sent` avant confirmation du canal.
- Réessayer les erreurs réseau et `5xx` du canal avec backoff ; conserver les notifications non marquées pour le prochain run.
- Segmenter les grands lots par priorité et taille maximale du canal.
- Pour les erreurs permanentes de payload, créer une alerte opérateur plutôt que boucler indéfiniment.

### Règles de sécurité

- Minimiser le contenu envoyé au canal : titre, description courte, priorité et identifiant interne si nécessaire.
- Ne pas inclure de PDF, données bancaires détaillées, données fiscales complètes ou secrets dans le message.
- Utiliser TLS et authentification pour les webhooks externes.
- Conserver une traçabilité backend de l'envoi avec canal, horodatage et identifiants, sans exposer le secret n8n.
