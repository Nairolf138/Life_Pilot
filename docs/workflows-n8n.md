# Workflows n8n

## Gmail ingestion

Le workflow `workflows/n8n/gmail-ingestion.json` automatise l'ingestion de PDF reçus par Gmail vers l'API Life Pilot.

### Déclenchement

- Planification recommandée : toutes les 3 heures en heures ouvrées, ou toutes les 6 heures pour un usage moins fréquent.
- La requête Gmail doit filtrer les nouveaux messages pertinents avec pièces jointes PDF, par exemple :
  `newer_than:7d has:attachment filename:pdf (facture OR invoice OR reçu OR receipt OR contrat OR échéance)`.

### Credentials Gmail attendus

Créer dans n8n un credential **Gmail OAuth2** nommé `Gmail Life Pilot` avec les droits suivants :

- accès en lecture aux messages Gmail ;
- accès aux métadonnées des messages ;
- accès au téléchargement des pièces jointes.

Scopes Google recommandés :

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.metadata`

Le compte Gmail connecté doit être celui dont les documents doivent être ingérés. Le workflow ne supprime pas les emails et ne modifie pas leur contenu.

### Variables d'environnement n8n

Configurer les variables suivantes côté n8n :

| Variable | Description |
| --- | --- |
| `LIFEPILOT_API_URL` | URL de base de l'API, par exemple `https://api.example.com`. |
| `LIFEPILOT_N8N_SECRET` | Secret partagé envoyé dans l'en-tête `X-N8N-Secret`. |
| `LIFEPILOT_USER_ID` | UUID de l'utilisateur Life Pilot propriétaire des documents importés. |

### Configuration backend

L'API expose un endpoint interne :

```http
POST /internal/n8n/documents
X-N8N-Secret: <secret partagé>
Content-Type: multipart/form-data
```

Champs multipart attendus :

- `file` : PDF téléchargé depuis Gmail ;
- `user_id` : UUID utilisateur Life Pilot ;
- `document_type` : classification simple calculée par n8n ;
- `title` : sujet de l'email ou nom de la pièce jointe.

Le backend doit définir `N8N_INTERNAL_SECRET` avec la même valeur que `LIFEPILOT_N8N_SECRET`. Si ce secret n'est pas configuré, l'endpoint interne refuse les ingestions.

### Journalisation des erreurs

Le workflow contient une branche d'erreur qui journalise le nom du workflow, l'étape, le message d'erreur et l'horodatage. En production, remplacer le nœud de log par une destination opérée : Slack, email d'alerte, base d'audit ou outil d'observabilité.

## Notifications quotidiennes

Le workflow `workflows/n8n/notifications.json` orchestre l'envoi quotidien des notifications Life Pilot. Il sert de couche d'automatisation entre l'API interne, qui sélectionne les notifications à remettre, et le canal de diffusion configuré dans n8n.

### Déclenchement

- Le nœud **Tous les jours à 08:00** exécute le workflow une fois par jour.
- L'heure peut être adaptée dans n8n selon le fuseau cible et les préférences produit, par exemple 07:30 pour un digest matinal.

### Étapes du workflow

1. **Récupération des candidates** : le nœud HTTP `Récupérer les notifications candidates` appelle l'API interne `GET /internal/n8n/notifications/candidates` avec `mark_as_sent=false` afin de ne pas marquer une notification comme envoyée avant confirmation du canal.
2. **Regroupement par priorité** : le nœud Code `Regrouper par priorité` accepte une réponse sous forme de tableau ou enveloppée dans `candidates`, `notifications` ou `data`. Il produit un item par priorité (`critical`, `urgent`, `warning`, `info`) trié de la priorité la plus élevée à la plus faible.
3. **Envoi via canal configuré** : le nœud `Envoyer via canal configuré` poste chaque groupe vers l'URL fournie par `LIFEPILOT_NOTIFICATION_CHANNEL_URL`. Le payload contient la source, le canal logique, la priorité, le nombre de notifications et la liste des notifications.
4. **Retour backend** : après un envoi sans erreur n8n, le nœud `Marquer les notifications envoyées` appelle `POST /internal/n8n/notifications/mark-sent` avec les identifiants du groupe, le canal et l'horodatage d'envoi.
5. **Gestion des erreurs** : deux branches journalisent séparément les erreurs de récupération des candidates et les erreurs du canal. Une erreur de canal ne déclenche pas le marquage comme envoyé, ce qui permet une nouvelle tentative lors d'une exécution ultérieure.

### Variables d'environnement n8n

Configurer les variables suivantes côté n8n :

| Variable | Description |
| --- | --- |
| `LIFEPILOT_API_URL` | URL de base de l'API, par exemple `https://api.example.com`. |
| `LIFEPILOT_N8N_SECRET` | Secret partagé envoyé dans l'en-tête `X-N8N-Secret` pour les appels internes. |
| `LIFEPILOT_NOTIFICATIONS_LIMIT` | Nombre maximal de candidates récupérées par exécution. Valeur par défaut du workflow : `100`. |
| `LIFEPILOT_NOTIFICATION_CHANNEL` | Nom logique du canal cible, par exemple `email`, `telegram`, `whatsapp` ou `n8n_webhook`. Valeur par défaut : `n8n_webhook`. |
| `LIFEPILOT_NOTIFICATION_CHANNEL_URL` | URL du canal réellement appelé par n8n : webhook, passerelle email, bot Telegram, passerelle WhatsApp ou service interne. |
| `LIFEPILOT_NOTIFICATION_CHANNEL_AUTH` | Valeur optionnelle de l'en-tête `Authorization` envoyée au canal configuré. |

### Contrat API attendu

Le workflow attend les endpoints internes suivants, protégés par `X-N8N-Secret` :

```http
GET /internal/n8n/notifications/candidates?limit=100&mark_as_sent=false
X-N8N-Secret: <secret partagé>
```

Réponse acceptée :

```json
{
  "candidates": [
    {
      "id": "notification-or-reminder-id",
      "reminder_id": "optional-reminder-id",
      "user_id": "user-id",
      "title": "Titre",
      "description": "Message à envoyer",
      "severity": "urgent",
      "priority": "urgent",
      "channels": ["email"],
      "deduplication_key": "reminder:..."
    }
  ]
}
```

Le workflow accepte aussi un tableau JSON direct. Chaque notification doit fournir `id` ou `reminder_id` afin de pouvoir être marquée comme envoyée.

```http
POST /internal/n8n/notifications/mark-sent
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

Corps envoyé par n8n :

```json
{
  "notification_ids": ["notification-or-reminder-id"],
  "priority": "urgent",
  "channel": "email",
  "sent_at": "2026-07-11T08:00:00.000Z"
}
```

Le backend doit seulement marquer comme envoyées les notifications listées lorsque le canal a accepté le groupe. En cas d'échec réseau ou applicatif sur le canal, le workflow journalise l'erreur et n'appelle pas l'endpoint de marquage.

### Journalisation des erreurs de canal

Le nœud `Journaliser erreurs de canal` écrit un objet JSON dans les logs n8n avec le workflow, l'étape, le message d'erreur, la priorité et les identifiants concernés. En production, ce nœud peut être remplacé ou complété par une alerte Slack, email d'astreinte, entrée d'audit ou intégration d'observabilité.

## Surveillance hebdomadaire des abonnements

Le workflow `workflows/n8n/subscription-monitor.json` automatise la surveillance des prélèvements récurrents afin de transformer les récurrences détectées en contrats suivis et en alertes actionnables.

### Déclenchement

- Le nœud **Chaque lundi à 06:00** exécute le workflow une fois par semaine.
- La fréquence peut être adaptée dans n8n si l'analyse bancaire est plus ou moins coûteuse, mais une cadence hebdomadaire limite le bruit tout en détectant rapidement les nouveaux abonnements et les hausses de prix.

### Étapes du workflow

1. **Lancement ou récupération de l'analyse** : le nœud HTTP `Lancer ou récupérer l'analyse` appelle `POST /internal/n8n/recurrences/analyze` avec l'utilisateur cible, une fenêtre d'analyse et une clé d'idempotence hebdomadaire. Le mode `launch_or_get` permet au backend de lancer une analyse si nécessaire ou de renvoyer un résultat déjà calculé pour la même période.
2. **Détection des nouveaux abonnements** : le nœud Code `Normaliser récurrences` transforme les détections en items n8n homogènes et marque `is_new_subscription` lorsque le backend signale un nouveau prélèvement récurrent ou une récurrence sans contrat associé.
3. **Détection des variations de prix** : le même nœud expose `has_price_variation` lorsque les alertes de l'analyse contiennent une hausse de prix. Le nœud `Variations de prix ?` isole ensuite ces cas pour déclencher un rappel ou une notification.
4. **Création ou mise à jour des contrats** : le nœud `Créer ou mettre à jour les contrats` appelle `POST /internal/n8n/contracts/upsert-from-recurrence` pour créer un contrat `to_review` ou mettre à jour un contrat existant à partir de la suggestion de récurrence.
5. **Création de rappels ou notifications** : le nœud `Créer rappels ou notifications` appelle `POST /internal/n8n/subscription-monitor/reminders` pour créer les rappels, notifications in-app ou alertes de validation nécessaires, notamment en cas de hausse de prix.
6. **Journalisation** : les nœuds `Journaliser erreurs analyse` et `Journaliser résultat` consignent les erreurs d'analyse et le statut des écritures effectuées par le workflow.

### Variables d'environnement n8n

Configurer les variables suivantes côté n8n :

| Variable | Description |
| --- | --- |
| `LIFEPILOT_API_URL` | URL de base de l'API, par exemple `https://api.example.com`. |
| `LIFEPILOT_N8N_SECRET` | Secret partagé envoyé dans l'en-tête `X-N8N-Secret` pour les appels internes. |
| `LIFEPILOT_USER_ID` | UUID de l'utilisateur Life Pilot dont les transactions doivent être analysées. |
| `LIFEPILOT_SUBSCRIPTION_LOOKBACK_DAYS` | Nombre de jours d'historique bancaire analysés. Valeur par défaut du workflow : `400`. |
| `LIFEPILOT_SUBSCRIPTION_ANALYSIS_MODE` | Mode d'analyse envoyé au backend. Valeur par défaut : `launch_or_get`. |

### Contrat API attendu

Le workflow suppose des endpoints internes protégés par `X-N8N-Secret`.

```http
POST /internal/n8n/recurrences/analyze
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

Corps envoyé par n8n :

```json
{
  "user_id": "user-id",
  "lookback_days": 400,
  "create_alerts": false,
  "idempotency_key": "subscription-monitor:2026-07-12",
  "mode": "launch_or_get"
}
```

Réponse attendue, directement ou enveloppée dans `report`, `analysis` ou `data` :

```json
{
  "analysis_id": "analysis-id",
  "user_id": "user-id",
  "detections": [
    {
      "key": "account:category:merchant:monthly",
      "period": "monthly",
      "merchant_or_label": "netflix",
      "average_amount": "13.49",
      "currency": "EUR",
      "first_seen_at": "2026-01-10",
      "last_seen_at": "2026-07-10",
      "transaction_ids": ["transaction-id"],
      "contract": {
        "provider": "Netflix",
        "name": "Netflix",
        "contract_type": "other",
        "payment_frequency": "monthly",
        "monthly_cost": "13.49",
        "yearly_cost": "161.88",
        "contract_id": null,
        "should_create": true
      },
      "alerts": [
        {
          "alert_type": "subscription_without_contract",
          "title": "Abonnement sans contrat associé : netflix",
          "severity": "warning"
        }
      ]
    }
  ]
}
```

```http
POST /internal/n8n/contracts/upsert-from-recurrence
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

Le payload contient la clé de récurrence, le fournisseur, le nom du contrat, la fréquence, les coûts estimés et les transactions sources. Le backend doit créer un contrat `to_review` si aucun contrat compatible n'existe, ou mettre à jour le coût et les métadonnées de suivi si un contrat est déjà rattaché.

```http
POST /internal/n8n/subscription-monitor/reminders
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

Le payload contient la clé de récurrence, les alertes associées, les transactions sources et `notify: true`. Le backend doit créer uniquement les rappels ou notifications utiles et éviter les doublons grâce à la clé de récurrence et aux types d'alertes.

### Journalisation et idempotence

La clé `subscription-monitor:<date ISO>` évite de relancer plusieurs fois la même analyse hebdomadaire si le workflow est rejoué. Les écritures backend doivent rester idempotentes côté contrats et rappels, car n8n peut réessayer un nœud après une erreur réseau.

## Rappels véhicules quotidiens

Le workflow `workflows/n8n/vehicle-reminders.json` automatise la surveillance des échéances liées aux véhicules afin de créer ou mettre à jour les rappels Life Pilot avant qu'une action ne soit urgente.

### Déclenchement

- Le nœud **Tous les jours à 07:30** exécute le workflow une fois par jour.
- L'horaire peut être ajusté selon le fuseau de l'utilisateur, par exemple avant le digest de notifications quotidiennes pour que les nouveaux rappels soient inclus dans la tournée du matin.

### Étapes du workflow

1. **Chargement des véhicules** : le nœud HTTP `Charger les véhicules` appelle `GET /internal/n8n/vehicles` avec l'utilisateur cible, les événements d'entretien et une fenêtre de projection.
2. **Vérification du contrôle technique** : le nœud Code `Vérifier échéances véhicules` lit `technical_inspection_due_date` et génère une action lorsque l'échéance est dépassée ou comprise dans la fenêtre configurée.
3. **Vérification de l'assurance** : le même nœud inspecte le contrat d'assurance rattaché au véhicule via `insurance_contract_id` ou l'objet `insurance_contract`, puis surveille `insurance_due_date`, `next_due_date`, `end_date` ou `renewal_date` selon les données exposées par le backend.
4. **Vérification des entretiens futurs** : les événements `events` ou `maintenance_events` sont analysés avec `next_due_date` et `next_due_mileage`. Le workflow signale les entretiens à venir par date ou par kilométrage proche.
5. **Création ou mise à jour des rappels** : le nœud `Créer ou mettre à jour les rappels` poste la liste normalisée vers `POST /internal/n8n/vehicle-reminders/upsert`. Chaque rappel porte une `deduplication_key` stable afin que le backend puisse faire un upsert idempotent plutôt qu'une création en doublon.
6. **Notification si action requise** : le nœud `Action requise ?` déclenche `Notifier actions requises` uniquement si des rappels doivent être traités. La notification est envoyée au canal configuré par n8n.
7. **Journalisation** : `Journaliser erreurs chargement` trace les erreurs API et `Journaliser résultat` trace le bilan de l'exécution.

### Variables d'environnement n8n

Configurer les variables suivantes côté n8n :

| Variable | Description |
| --- | --- |
| `LIFEPILOT_API_URL` | URL de base de l'API, par exemple `https://api.example.com`. |
| `LIFEPILOT_N8N_SECRET` | Secret partagé envoyé dans l'en-tête `X-N8N-Secret` pour les appels internes. |
| `LIFEPILOT_USER_ID` | UUID de l'utilisateur Life Pilot dont les véhicules doivent être surveillés. |
| `LIFEPILOT_VEHICLE_LOOKAHEAD_DAYS` | Nombre de jours d'anticipation pour le contrôle technique, l'assurance et les entretiens datés. Valeur par défaut du workflow : `90`. |
| `LIFEPILOT_VEHICLE_REMINDER_LEAD_DAYS` | Nombre de jours avant l'échéance utilisés pour positionner `reminder_date`. Valeur par défaut du workflow : `30`. |
| `LIFEPILOT_VEHICLE_MILEAGE_LOOKAHEAD` | Marge kilométrique avant une échéance d'entretien. Valeur par défaut du workflow : `1500`. |
| `LIFEPILOT_NOTIFICATION_CHANNEL` | Nom logique du canal cible, par exemple `email`, `telegram`, `whatsapp` ou `n8n_webhook`. Valeur par défaut : `n8n_webhook`. |
| `LIFEPILOT_NOTIFICATION_CHANNEL_URL` | URL du canal réellement appelé par n8n lorsqu'une action véhicule est requise. |
| `LIFEPILOT_NOTIFICATION_CHANNEL_AUTH` | Valeur optionnelle de l'en-tête `Authorization` envoyée au canal configuré. |

### Contrat API attendu

Le workflow suppose des endpoints internes protégés par `X-N8N-Secret`.

```http
GET /internal/n8n/vehicles?user_id=<uuid>&include_events=true&lookahead_days=90
X-N8N-Secret: <secret partagé>
```

Réponse acceptée, directement ou enveloppée dans `vehicles` ou `data` :

```json
{
  "vehicles": [
    {
      "id": "vehicle-id",
      "user_id": "user-id",
      "brand": "Renault",
      "model": "Clio",
      "registration_masked": "AB-***-CD",
      "technical_inspection_due_date": "2026-08-15",
      "insurance_contract_id": "contract-id",
      "insurance_contract": {
        "id": "contract-id",
        "renewal_date": "2026-09-01"
      },
      "mileage_current": 58500,
      "events": [
        {
          "id": "event-id",
          "title": "Vidange",
          "next_due_date": "2026-08-01",
          "next_due_mileage": 60000
        }
      ]
    }
  ]
}
```

```http
POST /internal/n8n/vehicle-reminders/upsert
X-N8N-Secret: <secret partagé>
Content-Type: application/json
```

Corps envoyé par n8n :

```json
{
  "user_id": "user-id",
  "generated_at": "2026-07-12T07:30:00.000Z",
  "action_required": true,
  "count": 1,
  "reminders": [
    {
      "type": "technical_inspection",
      "deduplication_key": "vehicle:vehicle-id:technical_inspection:2026-08-15",
      "vehicle_id": "vehicle-id",
      "user_id": "user-id",
      "title": "Contrôle technique à prévoir - Renault Clio AB-***-CD",
      "description": "Échéance contrôle technique le 2026-08-15.",
      "due_date": "2026-08-15",
      "reminder_date": "2026-07-16",
      "severity": "warning",
      "source_type": "vehicle",
      "source_id": "vehicle-id",
      "notification_channels": ["in_app", "email"]
    }
  ]
}
```

Le backend doit créer ou mettre à jour les rappels à partir de `deduplication_key`, `source_type`, `source_id` et `type`. Les rappels déjà terminés ou explicitement ignorés ne devraient pas être rouverts sans nouvelle échéance.

### Notification et idempotence

La notification de fin est volontairement séparée de l'upsert des rappels : elle n'est envoyée que lorsque le payload indique `action_required` ou que le backend retourne des rappels créés ou modifiés. Les écritures doivent rester idempotentes, car n8n peut rejouer un nœud après une erreur réseau ou une relance manuelle.
