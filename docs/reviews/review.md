---
status: pending
created: 2026-08-01T16:30:00
completed: 
---

## Cross-Step Review: re-centralize-shared-code

### Verdict
⚠️ Issues Found — 1 MAJOR, 3 patterns to address

### Summary

**0 BLOCKERs, 1 MAJOR, 3 🟡 patterns**

All three repos compose correctly — no fundamental contradictions. The library's dual-style search, pagination module, and accounting adapter correctly handle both servers' differing schemas (no `company_id` in investos, has `company_id` in companyos). Model registration at startup works in both servers. Deleted utility files are gone, no stale imports remain.

**The one MAJOR issue is that CompanyOS routers do not pass `dialect="sqlite"` to `apply_fuzzy_search`, violating Step 15 of the plan. This will cause runtime failures if CompanyOS ever runs against SQLite.**

---

### File-by-File Verdict

| File | Verdict | Note |
|---|---|---|
| **Library: `search.py`** | ✅ OK | Dual-style `.filter()`/`.where()`, enum exclusion, SQLite fallback — all correct |
| **Library: `pagination.py`** | ✅ OK | Matches investos signature byte-for-byte; optional FastAPI dep handled |
| **Library: `Utils/__init__.py`** | ✅ OK | Lazy `__getattr__` for pagination avoids hard FastAPI dependency |
| **Library: `sqlalchemy_adapter.py`** | ✅ OK | `hasattr` check for `company_id`, `UUID \| None` everywhere, `currency` param propagated |
| **Library: `engine.py`** | ✅ OK | `company_id: UUID \| None = None` correct; `currency` pass-through works |
| **Library: `models.py`** | ✅ OK | Registry unchanged; `_is_equivalent_model_registration` handles both enum styles |
| **Investos: `app.py`** | ✅ OK | Model registration before router mounts; `configure_native_fuzzy_search_support` kept local |
| **Investos: routers** | ✅ OK | Explicit columns for enum exclusion; `_SEARCH_DIALECT` passed; `run_sync` pattern correct |
| **Investos: deleted utils** | ✅ OK | All three removed; `projection_utils.py` kept (investos-specific) |
| **Investos: `test_search_utils.py`** | ✅ OK | Imports updated to library; tests updated to pass explicit columns |
| **CompanyOS: `main.py`** | ✅ OK | Model registration before router mounts; correct model classes passed |
| **CompanyOS: `routers/accounting.py`** | ⚠️ ISSUE | `run_sync` wrapping correct; router-local pagination deps preserve historical defaults; BUT no `dialect` param on fuzzy search calls |
| **CompanyOS: routers (13 others)** | ⚠️ ISSUE | All use `apply_fuzzy_search(stmt, q)` WITHOUT `dialect=` param |
| **CompanyOS: deleted utils** | ✅ OK | `accounting_utils.py` and `search_utils.py` removed; contact utils stay |
| **CompanyOS: tests** | ✅ OK | `test_accounting_logic.py` imports from library; `test_fuzzy_search.py` imports from library |

---

### 🔴 Cross-Step Critical

_None found._ No step N breaks a contract or invariant introduced in step M.

---

### 🔴 MAJOR — Must Fix

#### **1. CompanyOS routers missing `dialect` parameter (Plan Step 15 violation)**

**Affected files:** All 14 companyos routers: `accounting.py`, `companies.py`, `contacts.py`, `products.py`, `profiles.py`, `roles.py`, `departments.py`, `users.py`, `industries.py`, `countries.py`, `financials.py`, `competencies.py`, `professions.py`, `company_shareholders.py`

**The problem:** The plan (Step 15) explicitly states:
> "CompanyOS callers must pass `dialect="sqlite"` when running against SQLite, rather than relying on env-var auto-detection."

Every companyos router calls:
```python
stmt = apply_fuzzy_search(stmt, pagination.q)
```
with NO `dialect=` argument. The default `dialect="postgresql"` builds pg_trgm/unaccent operators that do not exist in SQLite. If companyos is deployed with SQLite (or tests switch to SQLite), ALL fuzzy-search endpoints will fail at query execution time with `no such function: f_unaccent`.

**Contrast:** Investos correctly declares `_SEARCH_DIALECT` at module level in each router:
```python
_SEARCH_DIALECT = "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql"
```
and passes it: `apply_fuzzy_search(stmt, q, columns..., dialect=_SEARCH_DIALECT)`

**Fix:** Add `DATABASE_URL` import and `_SEARCH_DIALECT` constant to each companyos router file. For routers that use auto-inference (no explicit columns), pass `dialect=_SEARCH_DIALECT`:
```python
from ..database import get_db
from ..config import DATABASE_URL
_SEARCH_DIALECT = "sqlite" if "sqlite" in DATABASE_URL else "postgresql"

# Then:
stmt = apply_fuzzy_search(stmt, pagination.q, dialect=_SEARCH_DIALECT)
```

A centralized alternative: export `_SEARCH_DIALECT` from `app/database.py` or a new `app/search_config.py` and import it in all routers, avoiding the duplication pattern investos used.

---

### 🟡 Cross-Step Patterns

#### **1. Explicit vs. inferred column divergence across servers**

**Investos** passes explicit column lists to `apply_fuzzy_search`:
```python
apply_fuzzy_search(stmt, q, models.ChartOfAccount.code, models.ChartOfAccount.name, ...)
```
This was a workaround needed before the library learned to exclude SAEnum columns from inference.

**CompanyOS** relies on auto-inference:
```python
apply_fuzzy_search(stmt, pagination.q)
```

The library now safely excludes SAEnum columns from inference (`_extract_string_columns` checks `not isinstance(col.type, SAEnum)`), so auto-inference is correct for both servers. The investos explicit-column approach is defensive but no longer necessary. Consider updating investos callers to use inference now that the library is safe — reduces maintenance burden when models add new text columns.

#### **2. Pagination dependency — library provides `PaginationDep`, neither server uses it directly**

The library defines:
```python
PaginationDep = Annotated[PaginationParams, Depends(pagination)]
```
with default `size=20`, `sort_by="id"`, `order="asc"`.

**Investos** does NOT use `PaginationDep` — it uses inline `Query(...)` parameters in each endpoint (e.g., `page: int = Query(1)`, `size: int = Query(20)`, etc.) This is a missed deduplication opportunity — investos endpoints could switch to `PaginationDep`.

**CompanyOS** creates router-local wrappers around `PaginationParams` for endpoints with different defaults:
```python
async def pagination_size_100(...):    # COA: size=100
async def pagination_journal_entries(...):  # sort_by=date, order=desc
```
These are valid customizations, but they duplicate the `Query(...)` parameter declarations instead of composing with the library's `pagination()` callable.

Consider adding a `pagination_with_defaults(size=100, sort_by="code", order="asc")` factory helper to the library so companyos can express overrides declaratively:
```python
pagination_coa = pagination_with_defaults(size=100)
COAPaginationDep = Annotated[PaginationParams, Depends(pagination_coa)]
```

#### **3. Separate `configure_native_fuzzy_search_support` implementations**

Investos defines its own `configure_native_fuzzy_search_support` in `app.py` as a startup health check. CompanyOS has NO equivalent startup check. Both servers now rely on the library's `apply_fuzzy_search`, which builds pg_trgm expressions. If the production PostgreSQL database is missing `pg_trgm`/`unaccent` extensions, companyos endpoints will fail at query time rather than at startup.

The plan (Step 9 constraint) says the startup check "belongs in the server" — but companyos doesn't have one. Consider adding a similar check to companyos's `database_lifespan`.

---

### 🟢 Notes

- **`_get_account_index(None)` behavior unchanged**: In the investos whole-ledger case (`company_id=None`), the adapter filters `account_owner == None`. This matches the old behavior and is correct for investos where accounts are scoped by `account_owner`. The empty index means no ancestor-based classification, but this was the same pre-migration.
- **`_get_posted_status()` handles both enum styles correctly**: companyos uses uppercase `JournalEntryStatus.POSTED.value` → detected by `hasattr(POSTED)`, investos uses lowercase → falls back to string `"posted"`. Both resolve to the correct filter value.
- **`hasattr(models.JournalEntry, "company_id")` correctly gates the filter in `_build_line_query`**: Returns False for investos (model has no `company_id`), True for companyos. This is the correct duck-typing approach.
- **Test suite reports** (lib: 75, investos: 110, companyos: 104) all pass — verified per user's report.
