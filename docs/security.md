# Sécurité

Ce document décrit les règles de sécurité applicables à Life Pilot. Les choix
par défaut doivent privilégier la confidentialité, la limitation des accès et la
réduction des données exposées.

## Principes par défaut

- **Lecture seule par défaut** : tout accès externe, connecteur, clé API ou lien
  technique doit être configuré en lecture seule tant qu'une permission
  d'écriture n'est pas explicitement justifiée, validée et tracée.
- **Principe de moindre privilège** : chaque compte, service, jeton, rôle de
  base de données et clé API doit disposer uniquement des permissions nécessaires
  à son usage réel.
- **Non-exposition publique par défaut** : aucune API privée, interface
  d'administration, base de données, bucket de fichiers, service interne ou
  stockage documentaire ne doit être exposé publiquement sans décision explicite,
  authentification forte et contrôle d'accès.
- **Fichiers privés** : les documents utilisateurs, exports, pièces jointes,
  sauvegardes et fichiers temporaires doivent être stockés dans des espaces
  privés et accessibles uniquement après vérification de l'identité et des droits.
- **Traçabilité** : les opérations sensibles doivent alimenter un audit trail
  exploitable, sans inclure de secrets ni de données personnelles inutiles.

## Gestion des secrets

- Le fichier `.env.example` sert uniquement de modèle documenté pour les
  variables d'environnement attendues.
- Le vrai fichier `.env` contient des secrets et des valeurs propres à chaque
  environnement : il ne doit jamais être versionné, commité ou poussé dans le
  dépôt Git.
- Aucun secret ne doit être stocké dans Git : mots de passe, tokens, clés API,
  clés privées, secrets OAuth, chaînes de connexion, clés de chiffrement,
  certificats privés et fichiers de configuration contenant des credentials sont
  interdits dans le dépôt.
- Les secrets doivent être transmis via un gestionnaire de secrets, un coffre
  chiffré ou un canal sécurisé, jamais par commit, ticket public, log ou message
  non chiffré.
- Les secrets au repos doivent être chiffrés avec une clé gérée hors du code
  source. La rotation des secrets doit être prévue dès qu'un secret est exposé,
  partagé trop largement ou devenu obsolète.
- Les environnements de développement, test, staging et production doivent avoir
  des secrets distincts.

## Chiffrement des secrets et données sensibles

- Les secrets doivent être chiffrés au repos dans le gestionnaire de secrets, le
  stockage applicatif et les sauvegardes.
- Les clés de chiffrement ne doivent pas être stockées à côté des données qu'elles
  protègent.
- Les communications contenant des secrets ou données personnelles doivent passer
  par TLS ou par un tunnel sécurisé.
- Les exports contenant des données sensibles doivent être chiffrés avant partage
  ou stockage longue durée.

## Clés API des connecteurs d'actifs

- Les clés API utilisées par les connecteurs d'actifs (Binance, eToro ou
  fournisseurs équivalents) doivent être configurées en lecture seule côté
  fournisseur.
- Les permissions d'achat, vente, virement, retrait, dépôt, effet de levier ou
  trading doivent rester désactivées pour toutes les clés utilisées par Life
  Pilot.
- Les credentials doivent être fournis uniquement par variables d'environnement
  ou par un coffre de secrets compatible ; ils ne doivent jamais être stockés en
  clair dans le code, la base de données ou les fichiers versionnés.

## Authentification

- Les mots de passe sont stockés uniquement sous forme de hash robuste et jamais
  en clair.
- Les routes privées doivent utiliser un jeton d'accès expirant et vérifié côté
  API.
- Les jetons de rafraîchissement ont une durée de vie plus longue mais restent
  expirables et doivent être conservés dans un stockage client sécurisé.
- Le schéma `users` garde un stockage minimal : identité, préférences, hash de
  mot de passe et indicateurs préparant l'activation future de MFA ou de passkey.
- L'activation d'une authentification forte par MFA et/ou passkey doit être
  prévue pour les comptes utilisateurs, les administrateurs et les accès aux
  services critiques.

## Stockage des documents et fichiers privés

- Les fichiers de documents utilisateurs sont stockés dans un espace privé et
  référencés en base via `documents.file_path`, `documents.file_hash` et
  `documents.mime_type`.
- Les chemins de stockage sont des chemins logiques internes, organisés par
  utilisateur et type de document ; ils ne doivent pas être exposés comme URL
  publique directe.
- Les fichiers ne doivent jamais être servis publiquement sans contrôle d'accès
  préalable : toute lecture doit vérifier l'utilisateur authentifié,
  l'appartenance du document et l'intégrité du fichier.
- Pour MinIO/S3, le bucket doit rester privé. Les liens pré-signés éventuels
  doivent être de courte durée et générés uniquement après autorisation métier.
- Les fichiers temporaires issus d'OCR, d'import, d'export ou de traitement de
  documents doivent être supprimés dès qu'ils ne sont plus nécessaires.

## Logs et règles de journalisation côté API

Les logs doivent permettre le diagnostic et l'audit sans exposer de données
sensibles. Côté API, les règles suivantes sont obligatoires :

- Ne jamais journaliser de tokens complets : JWT, refresh tokens, bearer tokens,
  session IDs, cookies d'authentification, tokens OAuth ou liens pré-signés.
- Ne jamais journaliser de clés API complètes, secrets de webhook, mots de passe,
  clés privées, chaînes de connexion ou valeurs d'en-têtes `Authorization`.
- Ne jamais journaliser d'IBAN complet. Si un IBAN est nécessaire au diagnostic,
  masquer la valeur et conserver uniquement un préfixe/suffixe limité, par
  exemple `FR76**************1234`.
- Ne pas journaliser d'emails complets si ce n'est pas strictement nécessaire.
  Préférer un identifiant utilisateur interne, un hash stable ou une forme
  masquée comme `j***@example.com`.
- Ne jamais journaliser le contenu intégral des documents, pièces jointes,
  résultats OCR, contrats, factures, relevés bancaires ou justificatifs.
- Ne pas écrire le corps complet des requêtes/réponses sur les routes manipulant
  des documents, transactions, comptes, contrats, paramètres utilisateur,
  authentification ou connecteurs externes.
- Utiliser des fonctions de redaction centralisées pour masquer les champs
  sensibles avant journalisation (`token`, `api_key`, `password`, `secret`,
  `iban`, `email`, `authorization`, `cookie`, etc.).
- Limiter les logs métier aux identifiants techniques, statuts, durées,
  compteurs, codes d'erreur et IDs de corrélation.
- Les logs d'erreur doivent éviter d'inclure des payloads bruts ; ils peuvent
  contenir une cause technique, un code d'erreur et un identifiant de trace.
- Les logs doivent être conservés pendant une durée limitée, protégés contre les
  accès non autorisés et exclus des dépôts Git.

## Audit trail

- Les actions sensibles doivent être tracées : connexion, échec de connexion,
  changement de mot de passe, changement de MFA/passkey, création ou révocation
  de clé API, accès à un document, export de données, suppression de fichier,
  changement de rôle et modification de configuration critique.
- Chaque événement d'audit doit inclure au minimum un horodatage, un identifiant
  d'utilisateur ou de service, une action, une ressource cible, un résultat et un
  identifiant de corrélation si disponible.
- L'audit trail ne doit pas contenir de secret, de token complet, de document
  complet ni de donnée personnelle excessive.
- Les journaux d'audit doivent être protégés contre la modification non autorisée
  et consultables uniquement par des rôles habilités.

## Sauvegardes chiffrées

- Les sauvegardes de base de données, fichiers, buckets, volumes et exports
  doivent être chiffrées au repos.
- Les clés de chiffrement des sauvegardes doivent être stockées séparément et
  accessibles uniquement aux personnes ou services autorisés.
- La restauration doit être testée régulièrement sur un environnement isolé.
- Les sauvegardes ne doivent pas être exposées publiquement ni copiées dans Git.
- La durée de rétention doit être définie selon les besoins métier et les
  contraintes légales applicables.

## Réseau et exposition des services

- Les services internes doivent rester non exposés publiquement par défaut.
- Pour l'accès distant, privilégier Tailscale, WireGuard ou un reverse proxy HTTPS
  sécurisé avec TLS à jour, authentification forte, restrictions d'IP si
  possible, en-têtes de sécurité et journalisation minimale.
- Les bases de données, files de messages, stockages objet, interfaces
  d'administration et outils de monitoring ne doivent pas être accessibles
  directement depuis Internet.
- Les ports inutiles doivent rester fermés et les règles réseau doivent être
  documentées.

## Plan de sauvegarde et restauration

- **Base PostgreSQL — quotidien** : exécuter chaque jour `scripts/backup.sh`
  depuis la racine du dépôt afin de produire un dump PostgreSQL horodaté et
  compressé. En production, utiliser `scripts/backup.sh --encrypt` avec la
  variable `BACKUP_ENCRYPTION_PASSPHRASE` fournie par un coffre de secrets, puis
  copier l'archive et son fichier `.sha256` vers un stockage privé hors serveur.
- **Documents — quotidien** : inclure chaque jour les documents MinIO ou le
  volume fichiers dans la même sauvegarde. Vérifier que `MINIO_BUCKET` pointe
  vers le bucket documentaire attendu et que le stockage de destination n'est ni
  public ni versionné dans Git.
- **Configuration n8n — hebdomadaire** : conserver au moins un export n8n par
  semaine. Le script tente d'exporter workflows et credentials chiffrés via le
  CLI n8n ; si l'export n'est pas possible, journaliser l'échec et planifier un
  export manuel avant toute modification majeure des automatisations.
- **Test de restauration — mensuel** : restaurer mensuellement la dernière
  sauvegarde sur un environnement isolé avec `scripts/restore.sh`, valider les
  contrôles minimaux post-restauration, puis vérifier manuellement un parcours
  métier incluant l'accès à la base, la présence de documents et un workflow n8n
  représentatif.
