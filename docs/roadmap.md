# Roadmap Life Pilot

Cette roadmap décrit une trajectoire de livraison progressive, organisée par phases fonctionnelles. Chaque phase doit produire un incrément utilisable, testable et documenté avant de passer à la suivante.

## Phase 0 : socle technique

**Objectif**

Mettre en place les fondations techniques nécessaires pour développer, tester, déployer et maintenir Life Pilot de manière fiable.

**Tâches principales**

- Définir l'architecture applicative et les principaux modules.
- Mettre en place la structure du projet, les conventions de code et la documentation développeur.
- Configurer l'environnement de développement, les variables de configuration et la gestion des secrets.
- Ajouter les outils de qualité : formatage, lint, tests automatisés et intégration continue.
- Définir le modèle de données initial et les mécanismes de migration.
- Mettre en place l'authentification, l'autorisation et les premiers contrôles de sécurité.

**Critère de fin**

Le socle permet de lancer l'application localement, d'exécuter les tests, de gérer les migrations et de déployer une version minimale sans fonctionnalité métier avancée.

**Dépendances**

- Choix de la stack technique.
- Accès aux environnements de développement et de déploiement.
- Décisions initiales sur la sécurité, le stockage et la confidentialité des données.

**Priorité**

Très haute.

**Risques**

- Architecture trop complexe ou insuffisamment évolutive.
- Mauvaise gestion des données sensibles dès le départ.
- Dette technique précoce si les outils de qualité ne sont pas automatisés.

## Phase 1 : transactions bancaires

**Objectif**

Permettre l'import, la consultation et la catégorisation initiale des transactions bancaires.

**Tâches principales**

- Définir le modèle de données des comptes, transactions, catégories et contreparties.
- Ajouter un import manuel de relevés bancaires, par exemple CSV ou formats bancaires courants.
- Normaliser les libellés, montants, dates, devises et statuts de transaction.
- Mettre en place une interface de consultation, recherche et filtrage des transactions.
- Ajouter une catégorisation manuelle et des règles simples de catégorisation.
- Préparer l'intégration future avec des agrégateurs bancaires si nécessaire.

**Critère de fin**

Un utilisateur peut importer un relevé bancaire, consulter ses transactions, corriger les données essentielles et affecter des catégories fiables.

**Dépendances**

- Phase 0 terminée.
- Formats de relevés bancaires ciblés identifiés.
- Règles de sécurité pour les données financières validées.

**Priorité**

Très haute.

**Risques**

- Formats bancaires hétérogènes et difficiles à normaliser.
- Doublons lors des imports successifs.
- Erreurs de catégorisation pouvant fausser les analyses futures.

## Phase 2 : emails et factures

**Objectif**

Centraliser les factures et informations financières provenant des emails ou de fichiers déposés par l'utilisateur.

**Tâches principales**

- Définir le modèle de données des documents, factures, fournisseurs et pièces jointes.
- Ajouter l'import manuel de fichiers PDF, images et emails exportés.
- Extraire les métadonnées essentielles : fournisseur, date, montant, TVA, échéance et référence.
- Mettre en place un espace de consultation, classement et recherche des documents.
- Prévoir une connexion email optionnelle avec autorisations explicites.
- Associer les documents à des catégories et à des contreparties connues.

**Critère de fin**

Un utilisateur peut ajouter des factures, les retrouver facilement et vérifier les informations extraites ou saisies manuellement.

**Dépendances**

- Phase 0 terminée.
- Phase 1 recommandée pour préparer les liens avec les transactions.
- Choix des technologies d'extraction de texte et d'analyse documentaire.

**Priorité**

Haute.

**Risques**

- Qualité variable des PDF, scans et images.
- Données personnelles sensibles présentes dans les emails et factures.
- Extraction automatique imparfaite nécessitant une validation utilisateur.

## Phase 3 : rapprochement automatique

**Objectif**

Relier automatiquement les transactions bancaires aux factures, emails et justificatifs correspondants.

**Tâches principales**

- Définir les règles de rapprochement basées sur montant, date, fournisseur, libellé et référence.
- Implémenter un score de confiance pour chaque correspondance proposée.
- Créer une interface de validation, correction et rejet des rapprochements.
- Gérer les cas complexes : paiements groupés, remboursements, acomptes et transactions fractionnées.
- Enregistrer l'historique des décisions utilisateur pour améliorer les suggestions.
- Ajouter des tests sur des jeux de données représentatifs.

**Critère de fin**

Le système propose des rapprochements pertinents avec un score de confiance et permet à l'utilisateur de valider ou corriger chaque lien.

**Dépendances**

- Phase 1 terminée.
- Phase 2 terminée.
- Données suffisamment normalisées pour comparer transactions et documents.

**Priorité**

Haute.

**Risques**

- Faux positifs sur des montants récurrents ou fournisseurs similaires.
- Règles trop rigides pour couvrir les cas réels.
- Perte de confiance utilisateur si les suggestions sont peu explicables.

## Phase 4 : contrats, abonnements, rappels

**Objectif**

Suivre les contrats, abonnements et échéances importantes afin d'anticiper les renouvellements, résiliations et paiements récurrents.

**Tâches principales**

- Définir le modèle de données des contrats, abonnements, échéances et rappels.
- Détecter ou créer manuellement les paiements récurrents depuis les transactions.
- Associer contrats, factures et transactions récurrentes.
- Ajouter des rappels configurables pour renouvellement, préavis, échéance ou révision de tarif.
- Créer une vue synthétique des abonnements actifs, coûts mensuels et dates clés.
- Prévoir des notifications par canal configurable.

**Critère de fin**

L'utilisateur peut suivre ses contrats et abonnements, visualiser leurs coûts et recevoir des rappels avant les échéances critiques.

**Dépendances**

- Phase 1 terminée.
- Phase 2 recommandée.
- Phase 3 utile pour automatiser les associations.
- Système de notifications disponible.

**Priorité**

Moyenne à haute.

**Risques**

- Oubli ou mauvaise détection de certains abonnements.
- Notifications trop nombreuses ou mal configurées.
- Informations contractuelles incomplètes si les documents ne sont pas fournis.

## Phase 5 : véhicule

**Objectif**

Permettre le suivi des coûts, documents, entretiens et échéances liés aux véhicules de l'utilisateur.

**Tâches principales**

- Définir le modèle de données des véhicules, assurances, entretiens, contrôles techniques et dépenses associées.
- Ajouter la saisie des informations véhicule : immatriculation, kilométrage, carburant, assurance et financement.
- Associer automatiquement ou manuellement les transactions et factures liées au véhicule.
- Suivre les entretiens, réparations, contrôles techniques et échéances administratives.
- Produire une synthèse des coûts par véhicule et par période.
- Ajouter des rappels pour entretien, assurance, contrôle technique et renouvellements.

**Critère de fin**

L'utilisateur peut consulter le coût complet de chaque véhicule, retrouver les documents associés et être rappelé des échéances importantes.

**Dépendances**

- Phase 1 terminée.
- Phase 2 recommandée.
- Phase 4 recommandée pour les rappels et contrats.

**Priorité**

Moyenne.

**Risques**

- Données de kilométrage ou d'entretien rarement mises à jour.
- Difficulté à distinguer certaines dépenses véhicule dans les transactions.
- Variabilité des obligations selon pays ou juridiction.

## Phase 6 : patrimoine

**Objectif**

Offrir une vision consolidée du patrimoine, des actifs, passifs et évolutions financières de l'utilisateur.

**Tâches principales**

- Définir le modèle de données des actifs, passifs, valorisations et historiques.
- Ajouter les catégories de patrimoine : comptes, immobilier, placements, véhicules, dettes et autres biens.
- Permettre la saisie manuelle des valeurs et l'import de justificatifs.
- Calculer des synthèses : patrimoine brut, dettes, patrimoine net et évolution dans le temps.
- Relier les éléments patrimoniaux aux transactions, contrats et documents existants.
- Préparer des exports pour analyse personnelle ou partage contrôlé.

**Critère de fin**

L'utilisateur dispose d'un tableau de bord patrimonial clair, avec valorisations suivies dans le temps et documents associés.

**Dépendances**

- Phase 1 terminée.
- Phase 2 recommandée.
- Phase 5 utile pour intégrer les véhicules.
- Règles de confidentialité renforcées.

**Priorité**

Moyenne.

**Risques**

- Valorisation imprécise ou obsolète des actifs.
- Données très sensibles nécessitant une sécurité renforcée.
- Complexité excessive si trop de types d'actifs sont supportés dès le départ.

## Phase 7 : assistant fiscal

**Objectif**

Aider l'utilisateur à préparer ses informations fiscales à partir des transactions, documents, contrats et éléments patrimoniaux disponibles.

**Tâches principales**

- Identifier les données utiles à la préparation fiscale : revenus, dépenses déductibles, justificatifs et patrimoine.
- Créer des vues de synthèse par année fiscale et par catégorie.
- Associer les justificatifs aux lignes fiscales potentielles.
- Ajouter des alertes sur données manquantes ou incohérentes.
- Générer des exports structurés pour vérification par l'utilisateur ou un professionnel.
- Documenter clairement les limites de l'assistant et éviter toute déclaration automatique non validée.

**Critère de fin**

L'utilisateur peut préparer un dossier fiscal annuel structuré, retrouver les justificatifs pertinents et exporter les informations pour validation.

**Dépendances**

- Phase 1 terminée.
- Phase 2 terminée.
- Phase 3 recommandée.
- Phase 6 recommandée pour les éléments patrimoniaux.
- Connaissance des règles fiscales ciblées par pays ou juridiction.

**Priorité**

Moyenne.

**Risques**

- Réglementation fiscale complexe et évolutive.
- Risque juridique si les recommandations sont présentées comme des conseils définitifs.
- Données incomplètes pouvant produire des synthèses trompeuses.

## Phase 8 : assistant conversationnel

**Objectif**

Permettre à l'utilisateur d'interroger ses données personnelles et d'être guidé dans les actions clés via une interface conversationnelle.

**Tâches principales**

- Définir les cas d'usage conversationnels prioritaires : recherche, synthèse, explication, rappel et aide à la décision.
- Mettre en place une couche d'accès contrôlé aux données utilisateur.
- Ajouter des réponses sourcées vers les transactions, documents, contrats ou tableaux de bord concernés.
- Implémenter des garde-fous sur les actions sensibles et les recommandations financières, fiscales ou administratives.
- Permettre la création assistée de rappels, catégories, règles ou rapprochements après confirmation utilisateur.
- Mesurer la qualité des réponses et prévoir une boucle de feedback.

**Critère de fin**

L'utilisateur peut poser des questions en langage naturel, obtenir des réponses vérifiables et déclencher certaines actions simples après confirmation explicite.

**Dépendances**

- Phases 1 à 4 terminées pour disposer de données utiles et structurées.
- Phases 6 et 7 recommandées pour les questions patrimoniales et fiscales.
- Politique de confidentialité, sécurité et audit des accès aux données.

**Priorité**

Moyenne à basse pour le lancement initial, puis élevée après stabilisation des données.

**Risques**

- Réponses incorrectes ou insuffisamment sourcées.
- Accès trop large aux données personnelles.
- Automatisation d'actions sensibles sans validation claire.
- Attentes utilisateur trop élevées par rapport aux capacités réelles de l'assistant.
