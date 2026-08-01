---
status: in_progress
created: 2026-08-01T00:00:00
completed:
---

# Plan : Suppression de la dépendance `fortyfour` (44Packages) des deux serveurs FastAPI

## Contexte

Les serveurs **companyos** (sync SQLAlchemy) et **investos** (async SQLAlchemy) dépendent du package partagé `fortyfour` (du repo `44Packages`) pour trois fonctionnalités :

1. **Recherche floue** (`apply_fuzzy_search`) — ~14 routeurs dans companyos, wrapper dans investos
2. **Validation comptable** (`validate_journal_entry_lines`) — les deux serveurs
3. **Rapports comptables** (`generate_trial_balance`, `assert_company_owns_accounts`) — les deux serveurs

L'objectif est de supprimer cette dépendance et d'inliner uniquement les fonctions utilisées, en profitant d'opportunités de simplification majeures :

- **Plus de `FortyFour.models.configure()`** — chaque serveur utilise ses propres modèles directement
- **Plus de `hasattr(JournalEntry, "company_id")`** — chaque serveur connaît son schéma
- **Plus de pattern Strategy** — logique Syscohada en dur
- **Plus de `_assert_configured()`** — suppression des gardes

### Différences clés entre les serveurs

| Caractéristique | companyos | investos |
|---|---|---|
| ORM | Sync (Session) | Async (run_sync pour trial_balance) |
| `JournalEntry.company_id` | OUI (Colonne directe) | NON |
| `ChartOfAccount.account_owner` | OUI (nullable) | OUI (non-nullable) |
| `JournalEntryStatus` | `str, Enum` | `enum.Enum` (SAEnum) |
| `apply_fuzzy_search` | Appel direct via `from FortyFour import` | Wrappé dans `api/utils/search_utils.py` |

---

## Délégation

- [ ] `Code Architect` needed? **Non** — les fichiers à créer sont déjà identifiés (2 nouveaux fichiers par serveur)
- [ ] `UI Designer` needed? **Non** — pas de composant visuel

---

## Étapes

### Groupe 1 — companyos : Créer `app/utils/search_utils.py` (fuzzy search)

1. **Créer `app/utils/search_utils.py` avec les fonctions de recherche floue**
   - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/companyos/app/utils/search_utils.py` (nouveau fichier)
   - **Contenu à copier depuis** `44Packages/src/FortyFour/Utils/search.py` :
     - `_SEARCHABLE_TYPES`
     - `_extract_string_columns(model)` — extrait les colonnes String/Text d'un modèle
     - `_resolve_columns(query, items)` — résout les colonnes à partir d'une Query ou de classes modèles
     - `fuzzy_match(column, term)` — condition de match flou (`<%`)
     - `fuzzy_similarity(column, term)` — score de similarité trigram
     - `apply_fuzzy_search(query, term, *columns)` — applique le filtre ET le tri par pertinence
   - **Constraint:** Signature exacte préservée (`apply_fuzzy_search(query: Query, term: str, *columns)`). Les imports `from sqlalchemy import ...` et `from sqlalchemy.orm import Query` restent identiques.
   - **Constraint:** Aucune dépendance à `FortyFour` ou `44Packages`.
   - **Edge cases:** `term` vide → la fonction s'exécute quand même (filtre OR sur colonnes vides). Aucune colonne trouvée → retourne la query inchangée.
   - **Done when:** Le fichier existe et contient les 5 fonctions avec exactement la même logique que `44Packages/src/FortyFour/Utils/search.py`.
   - **Do NOT:** Modifier la logique des fonctions. Garder `_SEARCHABLE_TYPES = (String, Text)`.

2. **Remplacer tous les `from FortyFour import apply_fuzzy_search` dans les routeurs companyos**
   - **Target:** 14 fichiers routeurs :
     - `app/routers/accounting.py` (ligne 15)
     - `app/routers/companies.py` (ligne 16)
     - `app/routers/competencies.py` (ligne 8)
     - `app/routers/contacts.py` (ligne 25)
     - `app/routers/countries.py` (ligne 7)
     - `app/routers/departments.py` (ligne 8)
     - `app/routers/financials.py` (ligne 8)
     - `app/routers/industries.py` (ligne 8)
     - `app/routers/products.py` (ligne 16)
     - `app/routers/professions.py` (ligne 8)
     - `app/routers/profiles.py` (ligne 8)
     - `app/routers/roles.py` (ligne 8)
     - `app/routers/users.py` (ligne 11)
   - **Action:** Remplacer `from FortyFour import apply_fuzzy_search` par `from ..utils.search_utils import apply_fuzzy_search`
   - **Constraint:** Ne toucher QUE la ligne d'import. Les appels à `apply_fuzzy_search(query, q, ...)` ne changent pas.
   - **Edge cases:** `contacts.py` a 3 appels, `products.py` en a 2, `profiles.py` en a 2. Vérifier qu'aucun appel n'est cassé.
   - **Done when:** `grep -r "from FortyFour import apply_fuzzy_search" app/` ne retourne aucun résultat.
   - **Do NOT:** Changer le code qui appelle `apply_fuzzy_search`. Modifier uniquement l'import.

### Groupe 2 — companyos : Créer `app/utils/accounting_utils.py` (logique comptable)

3. **Créer `app/utils/accounting_utils.py` — Partie 1 : dataclasses, constantes et fonctions core**
   - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/companyos/app/utils/accounting_utils.py` (nouveau fichier)
   - **Contenu à inclure (depuis `44Packages/src/FortyFour/accounting/core.py` + `strategies/syscohada.py`) :**
     - `ZERO = Decimal("0.00")`
     - `AccountSnapshot` (dataclass, frozen, slots — lignes 75-83 de core.py)
     - `AccountClassification` (dataclass, frozen, slots — lignes 87-92 de core.py)
     - `to_decimal(value)` (lignes 119-122)
     - `get_line_value(line, field_name, default=ZERO)` (lignes 125-128)
     - `normalized_text_value(value)` (lignes 131-135)
     - `normalize_account_ids(account_ids)` (lignes 138-139)
     - `account_code(account)` (lignes 156-159)
     - `account_code_matches_prefixes(account, prefixes)` (lignes 298-300)
     - `resolve_pcg_class_with_source(account)` (lignes 162-183)
     - `infer_statement_role_from_pcg_class(pcg_class, account=None)` (lignes 190-232)
     - Constantes SYSCOHADA : `SYSCOHADA_FINANCING_CODE_PREFIXES`, `SYSCOHADA_INVESTING_CODE_PREFIXES`, `SYSCOHADA_OPERATING_CODE_PREFIXES`, `SYSCOHADA_TREASURY_CODE_PREFIXES` (depuis `strategies/syscohada.py` lignes 13-52)
     - `_syscohada_classify_statement_role(account, net_balance)` → logique de `SyscohadaStrategy.classify_statement_role` (syscohada.py lignes 56-71) + fallback `DefaultStrategy.classify_statement_role` (base.py lignes 26-28)
     - `_syscohada_classify_cash_flow_role(account)` → logique de `SyscohadaStrategy.classify_cash_flow_role` (syscohada.py lignes 73-82) + fallback `DefaultStrategy.classify_cash_flow_role` (base.py lignes 30-31 qui appelle `classify_cash_flow_account`)
     - `_syscohada_is_treasury_account(account)` → logique de `SyscohadaStrategy.is_treasury_account` (syscohada.py lignes 84-85)
     - `classify_account(account, account_index=None, net_balance=ZERO)` → logique simplifiée de core.py lignes 253-295, **sans paramètre strategy** (appels directs à `_syscohada_*`)
     - `build_trial_balance(company_id, items, start_date, end_date, generated_at, currency)` (core.py lignes 510-529)
     - `validate_journal_entry_lines(lines)` (core.py lignes 465-485)
   - **Constraint:** `classify_account` doit être simplifié : pas d'appel à `_resolve_accounting_strategy`, pas de `AccountingStrategy` Protocol, pas d'import de stratégies. Appeler directement `_syscohada_classify_statement_role`, `_syscohada_classify_cash_flow_role`, `_syscohada_is_treasury_account`.
   - **Constraint:** `_syscohada_classify_cash_flow_role` doit contenir le fallback `classify_cash_flow_account` en dur (logique de `DefaultStrategy.classify_cash_flow_role` → `classify_cash_flow_account` de core.py lignes 331-360).
   - **Constraint:** Tous les imports viennent de `decimal`, `datetime`, `uuid`, `typing`, `dataclasses` — aucune dépendance à `FortyFour` ou `sqlalchemy`.
   - **Constraint:** `PCG_CLASS_*` et `TREASURY_ACCOUNT_NAME_MARKERS` de core.py ne sont PAS nécessaires pour ces chemins d'appel → ne pas les inclure.
   - **Edge cases:** `classify_account` avec `account=None` → retourne `AccountClassification(None, "unknown", "operating", "unknown")`. `account_index` vide → pas de résolution hiérarchique.
   - **Done when:** Le fichier existe avec toutes les fonctions listées et les signatures correspondent.
   - **Do NOT:** Inclure les fonctions non utilisées (`build_balance_sheet`, `build_income_statement`, `build_cash_flow_statement`, `accumulate_cash_flow_line`, `allocate_cash_flow_amount`, `select_counterpart_lines_for_cash_flow`, `is_supporting_non_operating_result_account`, `is_treasury_account` générique, `_classify_cash_flow_role` générique, `classify_cash_flow_account` standalone, `statement_section`, `_resolve_accounting_strategy`). Inclure UNIQUEMENT les fonctions listées ci-dessus + leurs dépendances transitives.

4. **Créer `app/utils/accounting_utils.py` — Partie 2 : fonctions adaptateur SQLAlchemy**
   - **Target:** Même fichier `app/utils/accounting_utils.py` (ajout à la suite)
   - **Contenu à inclure (depuis `44Packages/src/FortyFour/accounting/sqlalchemy_adapter.py`) :**
     - `_to_account_snapshot(account)` → retourne un `AccountSnapshot` (lignes 33-42), adapté pour utiliser les modèles companyos directement (`models.ChartOfAccount` → type hint `ChartOfAccount`)
     - `_get_account_index(db, company_id)` → requête `db.query(models.ChartOfAccount).filter(models.ChartOfAccount.account_owner == company_id).all()` (lignes 45-52, simplifié — pas de `models.` indirect)
     - `_get_posted_status()` → retourne `models.JournalEntryStatus.POSTED.value` (lignes 146-151, simplifié — pas de `hasattr` ni `_assert_configured`)
     - `_build_line_query(db, company_id, start_date, end_date, currency)` → **HARDCODÉ pour companyos** : filtre `models.JournalEntry.company_id == company_id` (pas de `hasattr`). Lignes 154-178 simplifiées.
     - `_get_opening_balances(db, account_ids, before_date, company_id, currency)` (lignes 225-249)
     - `_group_posted_lines(db, company_id, start_date, end_date, account_types, currency, normalize_balances=True)` → **sans paramètre strategy** — utilise `classify_account` directement (lignes 252-352 simplifiées)
     - `generate_trial_balance(db, company_id, start_date, end_date, currency)` → **sans paramètre strategy** (lignes 355-380 simplifiées)
     - `assert_company_owns_accounts(db, company_id, lines)` (lignes 109-143, simplifié — pas de `_assert_configured`, pas de `models.` indirect)
   - **Constraint:** Tous les appels à `models.ChartOfAccount`, `models.JournalEntry`, etc. utilisent les imports directs depuis `..models`.
   - **Constraint:** Les imports sont : `from ..models import ChartOfAccount, JournalEntry, JournalEntryLine, JournalEntryAttachment, JournalEntryStatus`
   - **Constraint:** `_build_line_query` filtre TOUJOURS par `company_id` (pas de branche conditionnelle).
   - **Constraint:** `_get_posted_status` retourne directement `JournalEntryStatus.POSTED.value`.
   - **Edge cases:** `_get_opening_balances` avec `account_ids` vide → retourne `{}`. `_group_posted_lines` sans résultats → retourne `[]`. `_get_account_index` sans comptes → retourne `{}`.
   - **Done when:** Toutes les fonctions sont dans le fichier, aucune dépendance à `FortyFour.models` ou `_assert_configured`.
   - **Do NOT:** Inclure `_to_entry_line_snapshot`, `_to_journal_entry_snapshot`, `_validate_cash_flow_overrides`, `_get_posted_entries_with_lines`, `_get_treasury_balance`, `get_account_balance`, `generate_balance_sheet`, `generate_income_statement`, `generate_cash_flow_statement`. Uniquement les fonctions listées ci-dessus.

5. **Mettre à jour les imports dans `app/routers/accounting.py` (companyos)**
   - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/companyos/app/routers/accounting.py`
   - **Action:**
     - Supprimer lignes 15-20 : `from FortyFour import apply_fuzzy_search` et `from FortyFour.accounting import (...)`
     - Ajouter : `from ..utils.search_utils import apply_fuzzy_search`
     - Ajouter : `from ..utils.accounting_utils import assert_company_owns_accounts, generate_trial_balance, validate_journal_entry_lines`
   - **Constraint:** Les appels existants `validate_journal_entry_lines(lines)`, `assert_company_owns_accounts(db, company_id, lines)`, `generate_trial_balance(db=db, company_id=company_id, ...)` ne changent pas.
   - **Done when:** `grep "FortyFour" app/routers/accounting.py` ne retourne rien.
   - **Do NOT:** Modifier le corps des fonctions qui appellent ces utilitaires.

6. **Supprimer `FortyFour.models.configure(...)` de `app/main.py` (companyos)**
   - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/companyos/app/main.py`
   - **Action:**
     - Supprimer lignes 13-23 : le commentaire, `import FortyFour.models as ff_models`, et l'appel `ff_models.configure(...)`
   - **Constraint:** Aucun autre code dans `main.py` ne dépend de `FortyFour`.
   - **Done when:** `grep "FortyFour" app/main.py` ne retourne rien.
   - **Do NOT:** Modifier autre chose dans `main.py`.

7. **Mettre à jour les tests companyos**
   - **Target:**
     - `tests/test_fuzzy_search.py` : ligne 4 → `from app.utils.search_utils import apply_fuzzy_search`
     - `tests/test_accounting_logic.py` : ligne 5 → `from app.utils.accounting_utils import validate_journal_entry_lines`
   - **Constraint:** Les assertions et la logique de test ne changent pas.
   - **Done when:** Les tests passent après les changements d'import.
   - **Do NOT:** Modifier le corps des tests.

8. **Supprimer `fortyfour` du `pyproject.toml` companyos et lancer `uv sync`**
   - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/companyos/pyproject.toml`
   - **Action:**
     - Supprimer `"fortyfour",` de `[project] dependencies` (ligne 22)
     - Supprimer `fortyfour = { git = ... }` de `[tool.uv.sources]` (ligne 32)
   - **Constraint:** Le `uv.lock` doit être regénéré sans `fortyfour`.
   - **Done when:** `uv sync` réussit, `grep fortyfour pyproject.toml` ne retourne rien.
   - **Do NOT:** Supprimer d'autres dépendances.

### Groupe 3 — investos : Mettre à jour `api/utils/search_utils.py` (fuzzy search inline)

9. **Inliner `apply_fuzzy_search` directement dans `api/utils/search_utils.py` (investos)**
   - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/api/utils/search_utils.py`
   - **Action:**
     - Supprimer ligne 3 : `from FortyFour import apply_fuzzy_search as fortyfour_apply_fuzzy_search`
     - Ajouter les fonctions inline depuis `44Packages/src/FortyFour/Utils/search.py` :
       - `_SEARCHABLE_TYPES = (String, Text)` (adapter : utiliser `_is_plain_text_column` existante au lieu de `_SEARCHABLE_TYPES` + `_extract_string_columns`)
       - `fuzzy_match(column, term)` — retourne `func.f_unaccent(term).bool_op("<%")(func.f_unaccent(func.coalesce(column, "")))`
       - `fuzzy_similarity(column, term)` — retourne `func.word_similarity(...)`
     - Remplacer ligne 102 `return fortyfour_apply_fuzzy_search(...)` par la logique inline :
       ```python
       conditions = [fuzzy_match(col, query_text) for col in resolved_columns]
       statement = statement.where(or_(*conditions))
       if len(resolved_columns) == 1:
           relevance = fuzzy_similarity(resolved_columns[0], query_text)
       else:
           relevance = func.greatest(*[fuzzy_similarity(col, query_text) for col in resolved_columns])
       return statement.order_by(relevance.desc())
       ```
   - **Constraint:** La fonction `apply_fuzzy_search` existante dans `search_utils.py` garde sa signature actuelle (`apply_fuzzy_search(statement, query_text, *columns)`). Seul le corps change — l'appel à `fortyfour_apply_fuzzy_search` est remplacé par la logique inline.
   - **Constraint:** Le comportement reste identique : filtrage OR sur les colonnes + tri par pertinence décroissante.
   - **Constraint:** Les fonctions `_is_plain_text_column` et `_resolve_search_columns` existantes sont conservées telles quelles.
   - **Edge cases:** `query_text` vide → retour anticipé (déjà géré ligne 83). Aucune colonne résolue → retour anticipé (déjà géré ligne 99).
   - **Done when:** `grep "fortyfour" api/utils/search_utils.py` ne retourne rien.
   - **Do NOT:** Modifier `_is_plain_text_column`, `_resolve_search_columns`, `_infer_text_columns`, `configure_native_fuzzy_search_support`.

10. **Mettre à jour `tests/test_search_utils.py` (investos)**
    - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/tests/test_search_utils.py`
    - **Action:**
      - Ligne 23 : `monkeypatch.setattr(search_utils, "fortyfour_apply_fuzzy_search", fake_apply)` → supprimer cette ligne
      - Le test `test_postgres_fuzzy_search_infers_only_plain_text_columns` doit être adapté : au lieu de mocker `fortyfour_apply_fuzzy_search`, mocker `fuzzy_match` et `fuzzy_similarity` dans `search_utils` directement, ou tester l'output réel.
    - **Constraint:** Le test doit continuer à vérifier que seules les colonnes texte (pas ENUM) sont passées à la recherche.
    - **Done when:** Les tests passent.
    - **Do NOT:** Supprimer le test.

### Groupe 4 — investos : Créer `api/utils/accounting_utils.py` (logique comptable)

11. **Créer `api/utils/accounting_utils.py` — Partie 1 : dataclasses, constantes et fonctions core**
    - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/api/utils/accounting_utils.py` (nouveau fichier)
    - **Contenu :** IDENTIQUE à l'étape 3 (companyos) pour les dataclasses, constantes et fonctions core. Les fonctions purement logiques (`to_decimal`, `get_line_value`, `classify_account`, `build_trial_balance`, `validate_journal_entry_lines`, etc.) sont les mêmes.
    - **Constraint:** Mêmes que l'étape 3. Aucune dépendance à SQLAlchemy ou aux modèles investos pour cette partie.
    - **Done when:** Mêmes fonctions que l'étape 3, dans un nouveau fichier.
    - **Do NOT:** Copier les fonctions adaptateur SQLAlchemy à cette étape.

12. **Créer `api/utils/accounting_utils.py` — Partie 2 : fonctions adaptateur SQLAlchemy (investos)**
    - **Target:** Même fichier `api/utils/accounting_utils.py` (ajout à la suite)
    - **Contenu à inclure (depuis `sqlalchemy_adapter.py`, adapté pour investos) :**
      - `_to_account_snapshot(account)` → adapté pour les modèles investos (`ChartOfAccount` avec `SAEnum`)
      - `_get_account_index(db, company_id)` → requête sync `db.query(models.ChartOfAccount).filter(models.ChartOfAccount.account_owner == company_id).all()`
      - `_get_posted_status()` → retourne `models.JournalEntryStatus.POSTED.value` (investos a un `enum.Enum` avec `.value`)
      - `_build_line_query(db, company_id, start_date, end_date, currency)` → **HARDCODÉ pour investos** : PAS de filtre `company_id` (investos n'a pas cette colonne). Si `company_id` est fourni, on filtre via `ChartOfAccount.account_owner` après la jointure. Ou on ignore `company_id` au niveau de cette query et on filtre ailleurs.
      - `_get_opening_balances(db, account_ids, before_date, company_id, currency)`
      - `_group_posted_lines(db, company_id, start_date, end_date, account_types, currency, normalize_balances=True)` → sans paramètre strategy
      - `generate_trial_balance(db, company_id, start_date, end_date, currency)` → sans paramètre strategy
    - **Constraint:** `_build_line_query` pour investos : la jointure avec `ChartOfAccount` n'est PAS dans cette fonction (elle est dans `_group_posted_lines`). Le filtre `company_id` est omis. Si on veut filtrer par propriétaire, on le fait via `_get_account_index` + jointure dans `_group_posted_lines`.
    - **Constraint:** Les imports sont : `from ..models import ChartOfAccount, JournalEntry, JournalEntryLine, JournalEntryAttachment`
    - **Constraint:** `generate_trial_balance` est appelé via `db.run_sync(lambda sync_db: generate_trial_balance(sync_db, ...))` dans le routeur investos. La fonction doit donc être **synchrone** et accepter une session SQLAlchemy sync.
    - **Edge cases:** `_build_line_query` avec `company_id=None` → pas de filtre de propriété au niveau entry. Le filtrage par propriétaire se fait via la jointure ChartOfAccount dans `_group_posted_lines` (qui utilise `_get_account_index`).
    - **Done when:** Toutes les fonctions sont dans le fichier, prêtes à être appelées depuis le routeur.
    - **Do NOT:** Inclure `assert_company_owns_accounts` (non utilisé par investos dans le routeur principal). Inclure `_validate_cash_flow_overrides`, `_get_posted_entries_with_lines`, `_get_treasury_balance`, `generate_balance_sheet`, `generate_income_statement`, `generate_cash_flow_statement`, `get_account_balance`.

13. **Mettre à jour les imports dans `api/routers/accounting.py` (investos)**
    - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/api/routers/accounting.py`
    - **Action:**
      - Supprimer lignes 22-26 : le commentaire et `from FortyFour.accounting import (generate_trial_balance, validate_journal_entry_lines)`
      - Ajouter : `from ..utils.accounting_utils import generate_trial_balance, validate_journal_entry_lines`
    - **Constraint:** Les appels existants `validate_journal_entry_lines(line_dicts)` (lignes 321, 907) et `generate_trial_balance(sync_db, ...)` (ligne 798) ne changent pas.
    - **Done when:** `grep "FortyFour" api/routers/accounting.py` ne retourne rien.
    - **Do NOT:** Modifier le corps des fonctions.

14. **Supprimer `FortyFour.models.configure(...)` de `api/app.py` (investos)**
    - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/api/app.py`
    - **Action:**
      - Supprimer ligne 16 : `import FortyFour.models as ff_models`
      - Supprimer lignes 17-18 : imports de modèles qui étaient uniquement pour `ff_models.configure()`
      - Supprimer lignes 24-31 : le bloc `if not getattr(ff_models, "_configured", False): ff_models.configure(...)`
    - **Constraint:** Les imports de modèles aux lignes 17-18 (`from models.chart_of_accounts_model import ChartOfAccount`, etc.) sont-ils utilisés ailleurs dans `app.py` ? Vérifier. Si non, les supprimer aussi.
    - **Done when:** `grep "FortyFour\|ff_models" api/app.py` ne retourne rien.
    - **Do NOT:** Modifier la logique d'initialisation de l'app.

15. **Mettre à jour `convert_accounting_to_async.py` (investos)**
    - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/convert_accounting_to_async.py`
    - **Action:**
      - Remplacer `from FortyFour.accounting import (...)` par les imports depuis `api.utils.accounting_utils`
      - Remplacer `from utils.search import apply_fuzzy_search` (ligne 10) par `from api.utils.search_utils import apply_fuzzy_search`
    - **Constraint:** Ce fichier est un script de migration historique. Les imports corrigés doivent permettre au fichier de rester syntaxiquement valide.
    - **Done when:** `grep "FortyFour" convert_accounting_to_async.py` ne retourne rien.
    - **Do NOT:** Réécrire le fichier entier. Juste les imports.

16. **Supprimer `fortyfour` du `pyproject.toml` investos et lancer `uv sync`**
    - **Target:** `/Users/checomart/Dropbox/GitHub/python/fastapi/investos/pyproject.toml`
    - **Action:**
      - Supprimer `"fortyfour",` de `[project] dependencies` (ligne 23)
      - Supprimer `fortyfour = { git = ... }` de `[tool.uv.sources]` (ligne 34)
    - **Constraint:** Le `uv.lock` doit être regénéré sans `fortyfour`.
    - **Done when:** `uv sync` réussit, `grep fortyfour pyproject.toml` ne retourne rien.
    - **Do NOT:** Supprimer d'autres dépendances.

---

## Exécution parallèle

- [x] Ce plan contient des groupes parallélisables ? **Oui**
- **Groupes parallèles :**
  - **Groupe A** (companyos) : Étapes 1-8 — indépendant d'investos
  - **Groupe B** (investos) : Étapes 9-16 — indépendant de companyos
  - Les deux groupes ne partagent **aucun fichier**. Aucune dépendance entre eux.

---

## Résumé des fichiers modifiés/créés

### companyos
| Fichier | Action |
|---|---|
| `app/utils/search_utils.py` | **NOUVEAU** — 5 fonctions de fuzzy search |
| `app/utils/accounting_utils.py` | **NOUVEAU** — ~20 fonctions core + ~8 adaptateurs SQLAlchemy |
| `app/main.py` | Suppression `ff_models.configure()` |
| `app/routers/accounting.py` | Changement imports (2 lignes) |
| `app/routers/companies.py` | Changement import (1 ligne) |
| `app/routers/competencies.py` | Changement import (1 ligne) |
| `app/routers/contacts.py` | Changement import (1 ligne) |
| `app/routers/countries.py` | Changement import (1 ligne) |
| `app/routers/departments.py` | Changement import (1 ligne) |
| `app/routers/financials.py` | Changement import (1 ligne) |
| `app/routers/industries.py` | Changement import (1 ligne) |
| `app/routers/products.py` | Changement import (1 ligne) |
| `app/routers/professions.py` | Changement import (1 ligne) |
| `app/routers/profiles.py` | Changement import (1 ligne) |
| `app/routers/roles.py` | Changement import (1 ligne) |
| `app/routers/users.py` | Changement import (1 ligne) |
| `tests/test_fuzzy_search.py` | Changement import (1 ligne) |
| `tests/test_accounting_logic.py` | Changement import (1 ligne) |
| `pyproject.toml` | Suppression `fortyfour` (2 lignes) |

### investos
| Fichier | Action |
|---|---|
| `api/utils/search_utils.py` | **MODIFIÉ** — inline fuzzy_match/fuzzy_similarity, suppression import fortyfour |
| `api/utils/accounting_utils.py` | **NOUVEAU** — ~20 fonctions core + ~7 adaptateurs SQLAlchemy |
| `api/app.py` | Suppression `ff_models.configure()` et imports associés |
| `api/routers/accounting.py` | Changement imports (3 lignes) |
| `convert_accounting_to_async.py` | Changement imports (2 lignes) |
| `tests/test_search_utils.py` | Adaptation du mock fortyfour |
| `pyproject.toml` | Suppression `fortyfour` (2 lignes) |

---

## Vérification finale

Après toutes les étapes, exécuter dans chaque serveur :

```bash
grep -r "FortyFour\|fortyfour" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | grep -v "docs/"
```

**Attendu :** Aucun résultat (hors docs/ et fichiers markdown).

```bash
uv sync
```

**Attendu :** Succès, plus de package `fortyfour` dans le lock.
