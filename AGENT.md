# FortyFour (44Packages) - Master Blueprint for AI Agents

Ce document est la source de vérité pour le fonctionnement, l'architecture et les conventions de développement du package **FortyFour**. Tous les agents d'IA doivent impérativement s'y référer avant de modifier le code de cette bibliothèque.

## 1. Description du Projet
`FortyFour` est une bibliothèque Python hautes performances destinée à l'analyse financière quantitative basée sur les données de la SEC (EDGAR).
Son objectif principal est de minimiser les appels à l'API de la SEC grâce à un système de cache robuste, et de fournir un moteur déclaratif pour calculer des métriques financières complexes (Marge brute, Endettement, etc.) en lissant les différences déclaratives entre les entreprises.

## 2. Architecture en 4 Tiers (Standards de Conception)

Le projet repose sur 4 piliers fondamentaux. **Aucune nouvelle fonctionnalité ne doit contourner cette architecture.**

### 2.1. Tier de Persistance (`SECCache`)
- **Principe** : Tous les appels à l'API SEC *doivent* passer par le cache local (SQLite).
- **Règle** : Les agents ne doivent jamais utiliser `requests` ou `httpx` pour faire un appel direct à l'API SEC si une donnée est censée être en cache, afin d'éviter d'atteindre les limites de "Rate Limit" de la SEC.

### 2.2. Tier de Données (`Company` & `GAAP`)
- **Fichier de référence** : `src/FortyFour/Finance/company.py`
- **Règle (Enum GAAP)** : Toutes les notions comptables doivent être standardisées via la classe `GAAP (Enum)`. Si un nouveau concept financier est introduit (ex: "Research and Development Expense"), l'agent **doit** l'ajouter à l'enum `GAAP` avec ses tags XBRL (synonymes) correspondants. On ne hardcode jamais de tag brut dans la couche supérieure.
- **Lazy Loading** : Les requêtes lourdes (parsing de JSON) ne sont chargées en mémoire que lors du premier appel.

### 2.3. Tier Logique (`MetricRegistry`)
- **Principe** : La logique métier de l'analyse (les "formules" financières) vit ici. 
- **Règle** : Pour ajouter une nouvelle métrique (ex: ROCE), l'agent doit l'enregistrer dans le registre en définissant clairement ses "composants" (qui seront résolus par les synonymes XBRL) et sa fonction mathématique en Python.

### 2.4. Tier d'Exécution (`MetricEngine`)
- **Fichier de référence** : `src/FortyFour/Finance/engine.py`
- **Règle** : L'engin est responsable de croiser les métriques et de résoudre les décalages de dates (grâce aux jointures externes de `pandas`). Il est conçu pour être résilient : s'il manque un composant, il log une erreur mais ne fait jamais planter le processus batch.

### 2.5. Générateur de CLI (`OpenAPICLIGenerator`)
- **Fichier de référence** : `src/FortyFour/Utils/cli_generator.py`
- **Principe** : Permet de générer automatiquement une CLI Typer complète à partir d'une spécification OpenAPI.
- **Usage** : Utile pour synchroniser le `CompanyOS-CLI` avec les évolutions de l'API Server sans codage manuel redondant.

## 3. Conventions de Code

- **Langage** : Python 3.
- **Gestion des Dépendances** : Projet standard (utilisation de `setup.py` et `requirements.txt`).
- **Analyse de données** : Le projet repose fortement sur la librairie `pandas`.
- **Typage** : L'utilisation des "Type Hints" est fortement recommandée pour toute nouvelle fonction.
- **Logging** : Utiliser la librairie standard `logging` (`logging.info()`, `logging.error()`) plutôt que des `print()`.

## 4. Règle pour l'Ajout de Nouvelles Fonctionnalités

Lorsque vous (l'agent IA) ajoutez une nouveauté :
1. Cherchez si ce n'est pas déjà un outil existant dans `src/FortyFour/Utils` ou `src/FortyFour/Finance/utils.py`.
2. Si vous ajoutez un utilitaire majeur, référencez-le dans le `README.md`.
3. Assurez-vous que l'ajout ne casse pas la compatibilité descendante (les utilisateurs utilisent `Company(cik=...).get_financial(...)` de façon intensive).

## 5. Maintenance de ce Document
Les Agents IA sont **responsables** de la tenue à jour de ce fichier `AGENT.md`. Si un changement modifie la façon fondamentale dont `FortyFour` s'architecture, l'agent doit immédiatement refléter ce changement ici.
