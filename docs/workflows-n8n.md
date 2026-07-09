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
