# Sécurité

## Gestion des secrets

- Le fichier `.env.example` sert uniquement de modèle documenté pour les variables d’environnement attendues.
- Le vrai fichier `.env` contient des secrets et des valeurs propres à chaque environnement : il ne doit jamais être versionné, commité ou poussé dans le dépôt Git.
- Les secrets partagés entre environnements doivent être transmis via un gestionnaire de secrets ou un canal sécurisé, jamais par commit.

## Clés API des connecteurs d’actifs

- Les clés API utilisées par les connecteurs d’actifs (Binance, eToro ou fournisseurs équivalents) doivent être configurées en lecture seule côté fournisseur.
- Les permissions d’achat, vente, virement, retrait, dépôt, effet de levier ou trading doivent rester désactivées pour toutes les clés utilisées par Life Pilot.
- Les credentials doivent être fournis uniquement par variables d’environnement ou par un coffre de secrets compatible ; ils ne doivent jamais être stockés en clair dans le code, la base de données ou les fichiers versionnés.

## Authentification

- Les mots de passe sont stockés uniquement sous forme de hash robuste et jamais en clair.
- Les routes privées doivent utiliser un jeton d’accès expirant et vérifié côté API.
- Les jetons de rafraîchissement ont une durée de vie plus longue mais restent expirables et doivent être conservés dans un stockage client sécurisé.
- Le schéma `users` garde un stockage minimal : identité, préférences, hash de mot de passe et indicateurs préparant l’activation future de MFA ou de passkey.

## Amélioration prévue

- L’activation d’une authentification forte par MFA et/ou passkey est prévue comme amélioration de sécurité future.

## Stockage des documents

- Les fichiers de documents utilisateurs sont stockés dans un espace privé et référencés en base via `documents.file_path`, `documents.file_hash` et `documents.mime_type`.
- Les chemins de stockage sont des chemins logiques internes, organisés par utilisateur et type de document ; ils ne doivent pas être exposés comme URL publique directe.
- Les fichiers ne doivent jamais être servis publiquement sans contrôle d’accès préalable : toute lecture doit vérifier l’utilisateur authentifié, l’appartenance du document et l’intégrité du fichier.
- Pour MinIO/S3, le bucket doit rester privé. Les liens pré-signés éventuels doivent être de courte durée et générés uniquement après autorisation métier.
