# Architecture backend

## Décision

Le backend de Life Pilot sera construit en **Python avec FastAPI**.

Cette décision permet de concentrer les capacités documentaires, financières et IA dans un même écosystème Python, tout en conservant un frontend en TypeScript.

## Choix recommandé : FastAPI Python

FastAPI est recommandé comme socle de l’API backend pour les raisons suivantes :

- **OCR** : l’écosystème Python dispose de bibliothèques matures pour l’OCR et le prétraitement d’images, notamment pour nettoyer, convertir et analyser des documents scannés.
- **Extraction PDF** : Python offre de nombreuses solutions robustes pour lire, segmenter et extraire le contenu de fichiers PDF, qu’il s’agisse de texte natif, de tableaux ou de documents nécessitant un traitement OCR.
- **IA** : les SDK, bibliothèques de traitement du langage naturel, outils d’embeddings, pipelines RAG et frameworks d’orchestration IA sont majoritairement disponibles et bien maintenus en Python.
- **Parsing financier** : les traitements de relevés, factures, transactions, exports bancaires et données structurées ou semi-structurées sont facilités par l’écosystème Python de data processing.
- **Traitement documentaire** : les workflows de classification, normalisation, extraction d’entités, enrichissement et indexation documentaire s’intègrent naturellement dans une stack Python.

FastAPI apporte également :

- une définition claire des contrats HTTP via OpenAPI ;
- une validation de données typée avec Pydantic ;
- de bonnes performances pour les APIs asynchrones ;
- une intégration simple avec des workers Python pour les traitements longs.

## Alternative étudiée : NestJS TypeScript

NestJS TypeScript a été étudié comme alternative principale.

Ses avantages sont :

- cohérence de langage avec le frontend TypeScript ;
- architecture modulaire et structurée ;
- bon support des APIs REST, de la validation et de l’injection de dépendances ;
- écosystème mature pour les applications web classiques.

Cependant, NestJS est moins adapté aux besoins prioritaires du projet :

- les bibliothèques OCR et PDF avancées sont moins nombreuses ou nécessitent souvent de déléguer à des services externes ou à des scripts Python ;
- les pipelines IA et documentaires sont plus naturellement supportés en Python ;
- le parsing financier et l’analyse de données bénéficient davantage de l’écosystème Python ;
- utiliser NestJS aurait probablement conduit à une architecture hybride avec un backend Node.js appelant des workers ou microservices Python.

Cette alternative reste pertinente pour des cas d’usage orientés API web classique, mais elle ajoute de la complexité pour les traitements documentaires et IA centraux à Life Pilot.

## Conséquences sur l’architecture

L’architecture cible est séparée par responsabilités :

- **API Python** : exposée avec FastAPI, elle gère les routes HTTP, la validation des entrées, l’authentification, les réponses API et l’orchestration légère des cas d’usage.
- **Workers Python** : ils exécutent les traitements longs ou coûteux, comme l’OCR, l’extraction PDF, l’analyse IA, l’indexation documentaire et les imports financiers.
- **Frontend TypeScript** : il reste dédié à l’interface utilisateur, à l’expérience produit, à la gestion d’état côté client et à l’intégration avec l’API HTTP.
- **Connecteurs externes** : ils isolent les intégrations avec les services tiers, par exemple stockage de fichiers, IA, OCR, fournisseurs bancaires, messagerie ou services de notification.

Cette séparation évite de mélanger les responsabilités et permet de faire évoluer indépendamment l’interface, l’API, les traitements asynchrones et les intégrations externes.

## Conventions de nommage des modules backend

Les modules backend doivent suivre des conventions explicites et cohérentes :

- utiliser des noms de modules en **snake_case** ;
- nommer les fichiers selon leur responsabilité métier ou technique ;
- éviter les abréviations ambiguës ;
- regrouper les fonctionnalités par domaine métier lorsque cela est possible ;
- garder une nomenclature stable entre l’API, les services, les jobs et les connecteurs.

Exemples de modules attendus :

```text
backend/
  app/
    api/
      documents.py
      financial_accounts.py
    services/
      document_extraction_service.py
      financial_parsing_service.py
    jobs/
      run_ocr_job.py
      import_transactions_job.py
    connectors/
      openai_connector.py
      storage_connector.py
      bank_connector.py
```

Règles recommandées :

- les routes HTTP utilisent des noms orientés ressource, par exemple `documents.py` ou `transactions.py` ;
- les services métier utilisent le suffixe `_service.py` ;
- les jobs asynchrones utilisent le suffixe `_job.py` ;
- les connecteurs externes utilisent le suffixe `_connector.py` ;
- les modèles de données, schémas ou DTO doivent être nommés selon leur usage et leur domaine.

## Séparation des responsabilités backend

### API HTTP

La couche API HTTP doit :

- exposer les endpoints FastAPI ;
- valider les paramètres et corps de requête ;
- retourner des réponses normalisées ;
- déléguer la logique métier aux services ;
- déclencher des jobs asynchrones lorsque le traitement ne doit pas bloquer la requête.

Elle ne doit pas contenir de logique lourde d’OCR, d’IA, de parsing financier ou d’intégration externe.

### Services métier

La couche services métier doit :

- porter les règles métier ;
- orchestrer les opérations applicatives ;
- manipuler les entités et objets de domaine ;
- décider quand appeler un connecteur ou planifier un job ;
- rester testable indépendamment du protocole HTTP.

Les services ne doivent pas dépendre directement des détails de présentation du frontend.

### Jobs asynchrones

Les jobs asynchrones doivent :

- exécuter les traitements longs, coûteux ou différés ;
- gérer l’OCR, l’extraction de PDF, les imports, l’indexation et les analyses IA ;
- pouvoir être relancés ou surveillés ;
- produire des résultats persistés ou des événements exploitables par l’API.

Ils doivent être conçus pour limiter les effets de bord et faciliter la reprise après erreur.

### Connecteurs externes

Les connecteurs externes doivent :

- encapsuler les appels aux services tiers ;
- centraliser les détails d’authentification, formats d’API, timeouts et retries ;
- fournir une interface simple aux services métier ;
- éviter que le reste du backend dépende directement d’un fournisseur spécifique.

Cette isolation permettra de remplacer ou compléter un fournisseur sans réécrire la logique métier.

## OCR configurable

Le pipeline documentaire s'appuie sur une interface `OcrProvider` pour isoler le
fournisseur OCR du reste du backend. L'API peut donc recevoir un PDF ou une image,
extraire d'abord le texte natif lorsque le PDF en contient, puis déléguer à l'OCR
si le texte est absent ou insuffisant.

Les résultats OCR doivent produire :

- un texte normalisé destiné à alimenter `documents.extracted_text` ;
- un score ou statut de confiance stockable avec le document ;
- le statut persistant `extraction_status = ocr_processed` lorsque l'OCR a
  effectivement produit un texte exploitable.

L'OCR peut être désactivé selon l'environnement, par exemple en développement,
en test ou dans une installation sans dépendances système. Dans ce cas, le
pipeline conserve un statut indiquant qu'un OCR reste requis au lieu de bloquer
la création du document. L'implémentation locale prévue est basée sur Tesseract,
mais le contrat `OcrProvider` permet de la remplacer par un service managé, un
worker spécialisé ou un mock de test sans modifier les routes HTTP ni le modèle
de données.
