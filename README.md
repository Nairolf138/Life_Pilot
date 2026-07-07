# Life Pilot

Life Pilot est un assistant administratif et financier personnel pensé pour centraliser, automatiser et fiabiliser les tâches du quotidien : suivi budgétaire, rappels administratifs, organisation documentaire, automatisations métier et préparation de tableaux de bord exploitables.

## Vision du projet

L’objectif est de construire une plateforme modulaire capable de :

- agréger les informations personnelles utiles à la gestion administrative et financière ;
- automatiser les workflows répétitifs via des intégrations dédiées ;
- fournir une interface web claire pour consulter les données, déclencher des actions et suivre les statuts ;
- exposer une API backend robuste pour orchestrer la logique métier ;
- conserver une base de données versionnée, reproductible et facilement initialisable ;
- documenter les choix techniques afin de faciliter la contribution et l’exploitation du projet.

## Structure du dépôt

```text
.
├── apps/
│   ├── web/                 # Application Next.js
│   └── api/                 # API backend
├── database/
│   ├── migrations/          # Migrations SQL versionnées
│   └── seeds/               # Données initiales et jeux de démarrage
├── workflows/
│   └── n8n/                 # Workflows n8n exportés
├── scripts/                 # Scripts utilitaires locaux ou CI
├── docs/                    # Documentation technique
└── tests/
    ├── fixtures/            # Jeux de données fictifs
    └── integration/         # Tests d’intégration
```

## Prérequis prévus

Les outils exacts seront verrouillés au fur et à mesure de l’initialisation des modules. La cible actuelle est :

- Node.js LTS pour l’application web et les outils JavaScript/TypeScript ;
- un gestionnaire de paquets JavaScript, idéalement `pnpm` ;
- Docker et Docker Compose pour les services locaux ;
- une base de données SQL compatible avec les migrations du projet ;
- n8n pour concevoir, tester et exporter les workflows d’automatisation.

## Commandes locales prévues

Ces commandes documentent l’intention du futur environnement de développement. Elles seront activées lorsque les modules correspondants seront initialisés.

```bash
# Installer les dépendances du monorepo
pnpm install

# Lancer l’application web Next.js
pnpm --filter web dev

# Lancer l’API backend
pnpm --filter api dev

# Appliquer les migrations SQL
pnpm db:migrate

# Charger les données initiales
pnpm db:seed

# Exécuter les tests d’intégration
pnpm test:integration

# Exporter ou synchroniser les workflows n8n
pnpm workflows:export
```

## Statut des modules

| Module | Emplacement | Statut | Description |
| --- | --- | --- | --- |
| Application web | `apps/web/` | À initialiser | Interface utilisateur Next.js. |
| API backend | `apps/api/` | À initialiser | Services applicatifs et logique métier. |
| Base de données - migrations | `database/migrations/` | À initialiser | Historique SQL versionné. |
| Base de données - seeds | `database/seeds/` | À initialiser | Données de démarrage locales. |
| Workflows n8n | `workflows/n8n/` | À initialiser | Automatisations exportées depuis n8n. |
| Scripts utilitaires | `scripts/` | À initialiser | Aide au développement, à la CI et aux opérations. |
| Documentation technique | `docs/` | À initialiser | Décisions d’architecture, procédures et conventions. |
| Fixtures de test | `tests/fixtures/` | À initialiser | Données fictives réutilisables par les tests. |
| Tests d’intégration | `tests/integration/` | À initialiser | Scénarios de validation de bout en bout. |

## Prochaines étapes

1. Initialiser le workspace et le gestionnaire de paquets.
2. Créer le squelette Next.js dans `apps/web/`.
3. Définir le framework backend dans `apps/api/`.
4. Choisir le moteur SQL et l’outil de migration.
5. Ajouter les premiers workflows n8n exportés.
6. Mettre en place les premiers tests d’intégration.
