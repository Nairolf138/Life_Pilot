# Sécurité

## Gestion des secrets

- Le fichier `.env.example` sert uniquement de modèle documenté pour les variables d’environnement attendues.
- Le vrai fichier `.env` contient des secrets et des valeurs propres à chaque environnement : il ne doit jamais être versionné, commité ou poussé dans le dépôt Git.
- Les secrets partagés entre environnements doivent être transmis via un gestionnaire de secrets ou un canal sécurisé, jamais par commit.
