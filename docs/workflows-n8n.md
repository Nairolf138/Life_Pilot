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
