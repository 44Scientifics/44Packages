---
status: in_progress
created: 2026-08-01T12:00:00
completed:
---

# Plan: Re-centralize Shared Code Back Into the FortyFour Library

## Context

The `FortyFour` library at `/Users/checomart/Dropbox/GitHub/python/libs/44Packages` previously contained shared accounting, search, and pagination code used by both `investos` and `companyos` FastAPI servers. That shared code was **inlined** into both servers to remove the library dependency. Now the user wants the **opposite**: move the duplicated code back into the centralized `FortyFour` library.

### Current State

| Code | Library (`FortyFour`) | investos | companyos |
|---|---|---|---|
| **Fuzzy search** | `Utils/search.py` (PG-only, ORM Query style) | `api/utils/search_utils.py` (PG + SQLite fallback, Core `select()` style) | `app/utils/search_utils.py` (PG + SQLite fallback, Core `select()` style — same style as investos) |
| **Pure accounting** | `accounting/core.py` (complete, identical logic) | `api/utils/accounting_utils.py` (inlined, identical core) | `app/utils/accounting_utils.py` (inlined, identical core) |
| **Accounting adapter** | `accounting/sqlalchemy_adapter.py` (handles `company_id` conditionally via `hasattr`) | Inlined in `accounting_utils.py` (no `company_id` — `_build_line_query` skips filter, sync, wrapped via `AsyncSession.run_sync`) | Inlined in `accounting_utils.py` (always filters by `company_id`, now async `await db.execute(…)` — will become sync + `run_sync` after migration) |
| **Model registry** | `models.py` (exists, `configure()` system) | **NOT used** — imports `models` directly | **NOT used** — imports `..models` directly |
| **Pagination** | **Missing** | `api/utils/pagination.py` | Inlined in every router |
| **Projection** | **Missing** | `api/utils/projection_utils.py` (async-only, investos-specific) | **N/A** |
| **Contact utils** | **Missing** | **N/A** | `app/utils/contact_*.py` (companyos-specific) |

### Key Differences to Reconcile

1. **Sync vs Async**: Both investos and companyos are now async SQLAlchemy (`create_async_engine` + `AsyncSession`). The library's adapter is sync-only. Both servers wrap sync calls identically via `AsyncSession.run_sync(lambda sync_db: lib_func(sync_db, ...))`.
2. **`company_id`**: investos `JournalEntry` has **no** `company_id` column; companyos **has** one. The library's `_build_line_query` already handles this via `hasattr(models.JournalEntry, "company_id")`.
3. **SQLAlchemy style**: Both servers now use Core `select()` (2.0 style). The library's `apply_fuzzy_search` uses `.filter()` (ORM Query style). Duck-typing (try `.filter()`, fall back to `.where()`) means both consumers will only exercise the `.where()` path — this is fine.
4. **SQLite support**: investos's search has a SQLite LIKE fallback; the library does not.
5. **PostgreSQL extension check**: investos has `configure_native_fuzzy_search_support` (async); not needed in the library (consumers handle startup checks).

## Delegation

- [x] `Code Architect` needed? **Yes** — this task spans 6+ files across 3 repositories and introduces a new pagination module pattern.
- [ ] `UI Designer` needed? **No** — no visual component.

## Architecture Decision: Model Registry Pattern

The library's existing `FortyFour.models.configure()` pattern **must** be used. At startup, each server registers its own SQLAlchemy model classes. The library's adapter then uses these registered models. This is the **only** clean way to handle the `company_id` split between servers.

```python
# investos startup (sync models, used via run_sync)
import FortyFour.models as ff_models
from api import models
ff_models.configure(
    chart_of_account=models.ChartOfAccount,
    journal_entry=models.JournalEntry,
    journal_entry_line=models.JournalEntryLine,
    journal_entry_attachment=models.JournalEntryAttachment,
    journal_entry_status=models.JournalEntryStatus,
)

# companyos startup
import FortyFour.models as ff_models
from app import models
ff_models.configure(
    chart_of_account=models.ChartOfAccount,
    journal_entry=models.JournalEntry,
    journal_entry_line=models.JournalEntryLine,
    journal_entry_attachment=models.JournalEntryAttachment,
    journal_entry_status=models.JournalEntryStatus,
)
```

## Search Function: Dual-Style Support

The library's `apply_fuzzy_search` must accept both SQLAlchemy 1.x ORM `Query` objects (`.filter()` / `.order_by()`) and 2.0 Core `Select` statements (`.where()` / `.order_by()`). **Constraint**: do NOT use isinstance checks against private types. Use duck-typing: try `.filter()`, fall back to `.where()`.

Also add SQLite fallback parameter. The function signature becomes:

```python
def apply_fuzzy_search(statement, query_text, *columns, dialect: str = "postgresql") -> ...
```

## Steps

### Groupe 1 — Library Enhancements (séquentiel — order matters)

1. **Library: Add SQLite fallback to `apply_fuzzy_search`**
   - **Target:** `src/FortyFour/Utils/search.py`
   - **Constraint:** The function must accept both ORM `Query` (`.filter()`) and Core `Select` (`.where()`) objects via duck-typing. When `dialect="sqlite"`, use `LIKE` predicates. Backward compatibility: existing callers without the `dialect` param must still work (default "postgresql").
   - **Constraint:** Do NOT import `DATABASE_URL` or any app-specific config. The caller passes the dialect.
   - **Edge cases:** Empty query_text → return unchanged statement. No resolved columns → return unchanged statement. Multiple columns → OR them.
   - **Done when:** `tests/test_search.py` passes with a new SQLite test case.
   - **Do NOT:** Add async functions, add database connections, add FastAPI dependencies to the library.

2. **Library: Add pagination module**
   - **Target:** `src/FortyFour/Utils/pagination.py` (new file)
   - **Constraint:** Contains `PaginationParams` dataclass, `pagination()` async callable (FastAPI `Depends`-compatible), and `PaginationDep` type alias. Must match investos's current signature exactly.
   - **Constraint:** FastAPI must be an **optional** dependency of the library. If FastAPI is not installed, the module should only fail at import time when actually used.
   - **Edge cases:** `size=0` means unlimited (as in investos). `page >= 1`. `sort_by` defaults to "id".
   - **Done when:** The dataclass and Depends function exist and match the investos signature byte-for-byte.
   - **Do NOT:** Add any ORM logic, database queries, or non-pagination concerns to this module.

3. **Library: Update `Utils/__init__.py` exports**
   - **Target:** `src/FortyFour/Utils/__init__.py`
   - **Constraint:** Export `apply_fuzzy_search`, `fuzzy_match`, `fuzzy_similarity` from search. Export `PaginationParams`, `pagination`, `PaginationDep` from pagination (lazy-imported to avoid hard FastAPI dependency).
   - **Done when:** `from FortyFour.Utils import apply_fuzzy_search, PaginationParams` works.

4. **Library: Ensure `sqlalchemy_adapter.py` handles all cases**
   - **Target:** `src/FortyFour/accounting/sqlalchemy_adapter.py`
   - **Constraint:** `_get_posted_status()` must handle two enum patterns: `JournalEntryStatus.POSTED.value` (companyos: uppercase `POSTED`) and `JournalEntryStatus.posted.value` (investos: lowercase `posted`). The current fallback `"posted"` string is correct.
   - **Constraint:** `_build_line_query` already uses `hasattr(models.JournalEntry, "company_id")` — verify this works correctly with the model registry. The `company_id` parameter type must be `UUID | None` (Optional).
   - **Constraint:** `generate_trial_balance` signature must accept `company_id: UUID | None = None` to accommodate investos (where company_id is optional for the whole ledger view).
   - **Edge cases:** When `company_id` is None and the model HAS a `company_id` column, the query should NOT filter (full ledger view). When `company_id` is provided and the model LACKS the column, scoping happens via `ChartOfAccount.account_owner`.
   - **Done when:** All existing tests in `tests/test_accounting_adapter.py` pass unchanged.
   - **Do NOT:** Change the pure accounting logic in `core.py` — it is already correct.

5. **Library: Add/update `JournalEntryStatus` handling in model registry**
   - **Target:** `src/FortyFour/models.py`
   - **Constraint:** The `configure()` function already accepts `journal_entry_status`. Ensure it handles both enum styles: `JournalEntryStatus.posted` (lowercase) and `JournalEntryStatus.POSTED` (uppercase). The detection is in `_get_posted_status()` in the adapter — no changes needed here, just verification.
   - **Done when:** The registry accepts both enum styles without error.

### Groupe 2 — Investos Migration (séquentiel, depends on Groupe 1)

6. **Investos: Add FortyFour dependency**
   - **Target:** `pyproject.toml`
   - **Constraint:** Add `fortyfour` (or `FortyFour`) via `[tool.uv.sources]` git reference: `fortyfour = { git = "https://github.com/44Scientifics/44Packages.git", tag = "<NEW-TAG>" }`. The tag must exist before this step.
   - **Constraint:** Also add `fastapi` as it's already a dependency.
   - **Done when:** `uv lock` succeeds and `uv sync` installs the library.

7. **Investos: Register models with FortyFour at startup**
   - **Target:** `api/app.py` (or `api/database.py`)
   - **Constraint:** Call `FortyFour.models.configure(...)` before any router is mounted. Must pass investos's model classes: `ChartOfAccount`, `JournalEntry`, `JournalEntryLine`, `JournalEntryAttachment`, `JournalEntryStatus`.
   - **Edge cases:** investos `JournalEntry` has NO `company_id` column — this is fine, the adapter handles it.
   - **Done when:** Server starts without `FortyFour.models has not been configured` error.
   - **Do NOT:** Modify model classes themselves.

8. **Investos: Replace `accounting_utils.py` imports with library imports**
   - **Target:** `api/routers/accounting.py` (lines 21-22)
   - **Constraint:** Replace `from utils.accounting_utils import generate_trial_balance, validate_journal_entry_lines` with `from FortyFour.accounting import generate_trial_balance, validate_journal_entry_lines`.
   - **Constraint:** The `generate_trial_balance` call site uses `AsyncSession.run_sync(lambda sync_db: generate_trial_balance(sync_db, ...))` — ensure the library function signature is compatible (`db: Session, company_id: UUID | None = None, ...`).
   - **Edge cases:** investos calls `generate_trial_balance` with `company_id=None` for whole-ledger view — this must still work.
   - **Done when:** Trial balance endpoint returns identical results before/after migration.
   - **Do NOT:** Delete `accounting_utils.py` yet — keep as shim during transition.

9. **Investos: Replace `search_utils.py` imports with library imports**
   - **Target:** All routers that import `apply_fuzzy_search`: `portfolios.py`, `job_applications.py`, `accounting.py`, `budgets.py`, `stocks.py`
   - **Constraint:** Replace `from utils.search_utils import apply_fuzzy_search` with `from FortyFour.Utils import apply_fuzzy_search`.
   - **Constraint:** The investos code uses `apply_fuzzy_search(statement, query_text, ...)` on Core `select()` objects. The library's updated function must handle both styles (see Step 1). Pass `dialect="sqlite"` when `DATABASE_URL` starts with `sqlite`.
   - **Constraint:** Remove the `configure_native_fuzzy_search_support` call from investos startup (it's an investos concern, keep it in investos as a startup check — it's NOT going to the library).
   - **Edge cases:** SQLite databases → LIKE fallback must work. PostgreSQL w/o extensions → server should fail at startup (via the existing investos check).
   - **Done when:** Fuzzy search on all endpoints returns identical results.
   - **Do NOT:** Remove `configure_native_fuzzy_search_support` from investos — it's a startup health check that belongs in the server.

10. **Investos: Replace `pagination.py` imports with library imports**
    - **Target:** All routers that use pagination parameters (check which ones use `PaginationDep`)
    - **Constraint:** Replace `from utils.pagination import ...` (if used) with `from FortyFour.Utils import PaginationParams, pagination, PaginationDep`.
    - **Constraint:** If routers define pagination params inline (not using `PaginationDep`), switch them to use `PaginationDep`.
    - **Done when:** All list endpoints use the centralized pagination dependency.
    - **Do NOT:** Change pagination behavior or defaults.

11. **Investos: Remove inlined utility files**
    - **Target:** `api/utils/accounting_utils.py`, `api/utils/search_utils.py`, `api/utils/pagination.py`
    - **Constraint:** Delete only after ALL imports have been migrated and verified.
    - **Constraint:** `projection_utils.py` stays — it's investos-specific (async-only, has no counterpart in companyos).
    - **Done when:** Files are deleted and server starts without import errors.

### Groupe 3 — CompanyOS Migration [P] (parallel with Groupe 2 — no shared files)

12. **CompanyOS: Add FortyFour dependency**
    - **Target:** `pyproject.toml`
    - **Constraint:** Same as Step 6: git tag reference under `[tool.uv.sources]`.
    - **Done when:** `uv lock` and `uv sync` succeed.

13. **CompanyOS: Register models with FortyFour at startup**
    - **Target:** `app/main.py`
    - **Constraint:** Call `FortyFour.models.configure(...)` before the app starts serving. Pass companyos's model classes.
    - **Edge cases:** companyos `JournalEntry` HAS a `company_id` column — the adapter detects this and filters accordingly.
    - **Done when:** Server starts without errors.

14. **CompanyOS: Replace `accounting_utils.py` imports with library imports**
    - **Target:** `app/routers/accounting.py`
    - **Constraint:** Replace `from ..utils.accounting_utils import assert_company_owns_accounts, generate_trial_balance, validate_journal_entry_lines` with `from FortyFour.accounting import assert_company_owns_accounts, generate_trial_balance` and `from FortyFour.accounting.core import validate_journal_entry_lines`.
    - **Constraint:** companyos's `accounting_utils.py` is now fully async (`async def`, `AsyncSession`, `await db.execute(…)`). The library's functions are sync (`Session`). All call sites must be converted to the `AsyncSession.run_sync` pattern, identical to investos:
      - `generate_trial_balance` → `await db.run_sync(lambda sync_db: generate_trial_balance(sync_db, company_id=company_id, start_date=date_start, end_date=date_end))`
      - `assert_company_owns_accounts` → `await db.run_sync(lambda sync_db: assert_company_owns_accounts(sync_db, company_id, lines))`
      - `validate_journal_entry_lines` is pure (no DB calls, already sync) — import directly from `FortyFour.accounting.core`, no `run_sync` needed.
    - **Constraint:** `assert_company_owns_accounts` in the library's `engine.py` calls `_assert_configured()` and delegates to the adapter — verify the behavior is identical to the removed async wrapper.
    - **Edge cases:** The `currency` parameter used in investos's `generate_trial_balance` call may not be used in companyos — verify the library signature accepts it as optional.
    - **Done when:** All accounting endpoints return identical results.
    - **Do NOT:** Keep the async wrapper functions in companyos — they become unnecessary once the library provides the sync version.

15. **CompanyOS: Replace `search_utils.py` imports with library imports**
    - **Target:** All routers importing `apply_fuzzy_search`: `accounting.py`, `contacts.py`, `products.py`, `profiles.py`, `roles.py`, `companies.py`, `departments.py`, `users.py`, `industries.py`, `countries.py`, `financials.py`, `competencies.py`, `professions.py`
    - **Constraint:** Replace `from ..utils.search_utils import apply_fuzzy_search` with `from FortyFour.Utils import apply_fuzzy_search`.
    - **Constraint:** companyos's `apply_fuzzy_search` is now Core `select()`-based (same as investos). The library's duck-typed dual-style support (`.filter()` / `.where()`) is still fine — both consumers will only exercise the `.where()` path.
    - **Constraint:** companyos's inline search has a SQLite LIKE fallback with dialect auto-detection via `DATABASE_URL` check. The library version (Step 1) accepts an **explicit `dialect` parameter**. CompanyOS callers must pass `dialect="sqlite"` when running against SQLite, rather than relying on env-var auto-detection.
    - **Edge cases:** CompanyOS test suite runs against SQLite → must pass `dialect="sqlite"`. Production (PostgreSQL) → can rely on default `"postgresql"`.
    - **Done when:** All search endpoints return identical results on both PostgreSQL and SQLite.
    - **Do NOT:** Keep the `DATABASE_URL`-based dialect auto-detection in companyos — the library handles dialect via explicit parameter.

16. **CompanyOS: Replace inline pagination with library**
    - **Target:** All routers that define `page: int = Query(...)` and `size: int = Query(...)` inline
    - **Constraint:** Replace inline pagination params with `PaginationDep = Annotated[PaginationParams, Depends(pagination)]` in each router. Since companyos endpoints are now `async def`, the `Depends` injection in `pagination()` works identically to investos — no special handling needed.
    - **Constraint:** Some companyos routers may define additional query params beyond pagination — keep those, only replace the `page`/`size`/`q` params.
    - **Edge cases:** Router endpoints that have different defaults (e.g., `size=100` instead of `size=20`) — do NOT force the library default, keep existing behavior if it differs.
    - **Done when:** All list endpoints return identical paginated results.

17. **CompanyOS: Remove inlined utility files**
    - **Target:** `app/utils/accounting_utils.py`, `app/utils/search_utils.py`
    - **Constraint:** Delete only after ALL imports are migrated and verified.
    - **Constraint:** `contact_hierarchy.py`, `contact_links.py`, `contact_network_overview.py` stay — they are companyos-specific.
    - **Done when:** Files deleted, server starts clean.

### Groupe 4 — Library Tag & Final Verification (after both Groupe 2 and Groupe 3)

18. **Library: Tag a new release**
    - **Target:** Git tag on `44Packages` repo
    - **Constraint:** Tag after all library changes (Steps 1-5) are complete and all library tests pass.
    - **Done when:** Tag exists and both servers reference it in their `pyproject.toml`.

19. **Both servers: Run full test suites**
    - **Target:** `tests/` directories in both investos and companyos
    - **Constraint:** All existing tests must pass. No test changes allowed unless a test was coupled to the inlined file path (in which case update the import).
    - **Done when:** `pytest` exits 0 in both servers.

## Parallel Execution

- [x] Ce plan contient des groupes parallélisables ? **Yes**
- **Groupe 2** (Steps 6-11: investos migration) and **Groupe 3** (Steps 12-17: companyos migration) are **fully independent** — they touch different files in different repositories, no shared state, no dependencies between them.
- **Groupe 1** (Steps 1-5) must complete before both Groupe 2 and Groupe 3.
- **Groupe 4** (Steps 18-19) must wait for both Groupe 2 and Groupe 3.

## Risk Register

| Risk | Mitigation |
|---|---|
| `JournalEntryStatus` enum value differs (`.posted` vs `.POSTED`) | Library's `_get_posted_status()` already handles both via `hasattr(status, "value")` fallback. Verify with tests. |
| investos Core `select()` vs companyos ORM `query()` style mismatch in search | **Resolved.** Both servers now use Core `select()`. Duck-typing in `apply_fuzzy_search` (try `.filter()` first, fall back to `.where()`) still works, but both consumers exercise the `.where()` path. |
| `generate_trial_balance` signature differs (`company_id: UUID \| None` vs `company_id: UUID`) | Library already accepts `UUID \| None`. investos passes `None` for full ledger. |
| Both servers are now async; library adapter is sync → need `run_sync` everywhere | No library change needed. Both investos and companyos wrap sync calls identically: `await db.run_sync(lambda sync_db: lib_func(sync_db, ...))`. This is the same pattern already used by investos pre-migration. |
| `assert_company_owns_accounts` only exists in companyos | Library already has it in `engine.py`. After migration, companyos wraps it via `run_sync` (same as `generate_trial_balance`). investos doesn't need it. |
| Syscohada treasury prefix `"52"` | Both servers and the library already include `"52"`. Verified. |
