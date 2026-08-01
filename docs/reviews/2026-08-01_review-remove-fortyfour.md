---
status: pending
created: 2026-08-01T00:00:00
completed:
---

## Cross-Step Review: Remove FortyFour Dependency (companyos + investos)

### Verdict
⚠️ Issues Found — 1 cross-step critical, 2 cross-step patterns

### Summary
**1 🔴 critical** (broken import), **2 🟡 patterns** (inconsistency, dead import). 
No FortyFour references remain in any Python source, pyproject.toml, or uv.lock. 
Core accounting logic is correctly inlined and functionally identical between servers where it should be. 
Search utils are properly adapted per codebase conventions.

---

### 🔴 Cross-Step Critical

- **[Step 15 vs Step 12]** `assert_company_owns_accounts` imported from a module that doesn't export it.
  **Files:** `convert_accounting_to_async.py:12` vs `api/utils/accounting_utils.py` (investos).
  **Why:** Step 12 (plan) explicitly says "Do NOT: Inclure `assert_company_owns_accounts`" for investos because it's not used in the main router. However, Step 15 updated `convert_accounting_to_async.py` to import `assert_company_owns_accounts` from `api.utils.accounting_utils` — but this function doesn't exist in the investos module. The import would fail at runtime.
  **Mitigating:** The file `convert_accounting_to_async.py` has pre-existing SyntaxErrors (`async async def` on line 46, variable name mismatches on lines 139, 191) that already prevent it from running. This broken import is therefore latent.
  **Fix:** Either (a) add `assert_company_owns_accounts` to investos's `api/utils/accounting_utils.py` (adapting it for the investos schema — no `company_id` column on `JournalEntry`, filter via `ChartOfAccount.account_owner`), or (b) remove the import line from `convert_accounting_to_async.py` since the file is non-functional anyway. Option (b) is simpler and aligns with the plan's Step 12 constraint.

---

### 🟡 Cross-Step Patterns

- **[Inconsistency] `resolved_pcg_class` helper exists in investos but not companyos.**
  **Files:** `api/utils/accounting_utils.py:188-189` (investos) vs `app/utils/accounting_utils.py` (companyos).
  **Why:** Both servers inline the same logic (`resolve_pcg_class_with_source(account)[0]`). Investos extracted it into a named helper; companyos calls it inline in `_syscohada_classify_cash_flow_role`. The logic is identical, but the structure is inconsistent between the two servers. The plan says the core functions should be "identical" — this is a minor structural deviation.
  **Fix:** Either add `resolved_pcg_class` to companyos or remove it from investos for consistency. Not urgent — functionally equivalent.

- **[Duplication] `_build_line_query` signature differs but for documented reasons.**
  **Files:** `app/utils/accounting_utils.py:405-429` (companyos) vs `api/utils/accounting_utils.py:416-439` (investos).
  **Why:** companyos's `_build_line_query` always filters by `company_id` (hardcoded `JournalEntry.company_id == company_id`). investos's `_build_line_query` accepts `company_id` but ignores it in the query body (the model has no `company_id` column). Both are correct per their schemas, but the function signatures and docstrings create an expectation mismatch: a reader might think investos filters by `company_id` when it doesn't.
  **Fix:** investos's `_build_line_query` should explicitly document that `company_id` is accepted for call-site compatibility but not used in the WHERE clause. The existing module-level docstring does this, but the function-level docstring doesn't mention it.

---

### 🟢 Notes

- **`classify_account(None)` would crash** in both servers (AttributeError in `get_line_value(None, "account_type", "")` within `_syscohada_classify_cash_flow_role` fallback). The plan's edge case note said it should return `AccountClassification(None, "unknown", "operating", "unknown")` — this is incorrect. However, `classify_account(None)` is never called in practice (accounts are always fetched from `_get_account_index` before classification), so this is a documentation bug, not a runtime bug. Pre-existing in the original FortyFour code.

- **`JournalEntryAttachment` omitted from imports** — confirmed correct. None of the inlined functions reference it. Would have been a dead import.

- **`build_trial_balance company_id` type differs** (`UUID` in companyos, `UUID | None` in investos) — planned and correct. Investos allows trial balance for the full ledger when `company_id=None`.

- **`_get_posted_status()` enum member name differs** — `POSTED` in companyos vs `posted` in investos — both correct per their respective `JournalEntryStatus` definitions (`str, Enum` with uppercase members vs `enum.Enum` with lowercase members). Both evaluate to `"posted"` at runtime.

- **Import styles differ** — companyos uses relative imports (`from ..utils.accounting_utils`), investos uses absolute (`from utils.accounting_utils`) — both follow their codebase conventions. Plan deviation acknowledged by coder.

- **All 13 companyos routers** correctly updated from `from FortyFour import apply_fuzzy_search` to `from ..utils.search_utils import apply_fuzzy_search`.

- **Both `pyproject.toml` and `uv.lock`** have zero `fortyfour` references.

- **Test adaptations** look correct for both servers: companyos tests import from new locations, investos test mocks `fuzzy_match`/`fuzzy_similarity` directly instead of the old `fortyfour_apply_fuzzy_search`.

- **`app/main.py` (companyos)** and **`api/app.py` (investos)** no longer contain `FortyFour.models.configure()` or any FortyFour references.
