# Sécurité

## Gestion des secrets

- Le fichier `.env.example` sert uniquement de modèle documenté pour les variables d’environnement attendues.
- Le vrai fichier `.env` contient des secrets et des valeurs propres à chaque environnement : il ne doit jamais être versionné, commité ou poussé dans le dépôt Git.
- Les secrets partagés entre environnements doivent être transmis via un gestionnaire de secrets ou un canal sécurisé, jamais par commit.

## Authentification

- Les mots de passe sont stockés uniquement sous forme de hash robuste et jamais en clair.
- Les routes privées doivent utiliser un jeton d’accès expirant et vérifié côté API.
- Les jetons de rafraîchissement ont une durée de vie plus longue mais restent expirables et doivent être conservés dans un stockage client sécurisé.
- Le schéma `users` garde un stockage minimal : identité, préférences, hash de mot de passe et indicateurs préparant l’activation future de MFA ou de passkey.

## Amélioration prévue

- L’activation d’une authentification forte par MFA et/ou passkey est prévue comme amélioration de sécurité future.
