# Accounting Hierarchical Classification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace fragile account-type heuristics with a deterministic classification pipeline that uses optional `parent_id` ancestry first, six-digit PCG codes second, and weak fallbacks only when necessary.

**Architecture:** Introduce a canonical account-classification layer in `src/FortyFour/accounting/core.py`, then refactor `src/FortyFour/accounting/sqlalchemy_adapter.py` so every financial statement is assembled from that shared classifier. Support `parent_id` as an optional consumer-owned field by reading it defensively from injected SQLAlchemy models.

**Tech Stack:** Python, SQLAlchemy, pytest, dataclasses, Decimal

---

### Task 1: Add failing tests for code-first classification

**Files:**
- Modify: `tests/test_accounting_core.py`
- Modify: `src/FortyFour/accounting/core.py:139-220`

**Step 1: Write the failing test**

```python
def test_resolved_pcg_class_prefers_six_digit_code_when_present() -> None:
    account = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        code="512100",
        name="Main bank",
        account_type="asset",
        account_class=None,
    )

    assert resolved_pcg_class(account) == 5
```

```python
def test_statement_role_uses_pcg_code_when_account_type_is_wrong() -> None:
    account = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        code="707000",
        name="Sales",
        account_type="asset",
        account_class=None,
    )

    classification = classify_account(account)

    assert classification.statement_role == "revenue"
    assert classification.classification_source == "code"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_accounting_core.py -k "pcg_class or statement_role_uses_pcg_code" -v`

Expected: FAIL because `classify_account` does not exist yet and the current implementation does not expose a canonical statement role.

**Step 3: Write minimal implementation**

Add a canonical dataclass and a minimal classifier in `src/FortyFour/accounting/core.py`:

```python
@dataclass(frozen=True, slots=True)
class AccountClassification:
    pcg_class: int | None
    statement_role: str
    cash_flow_role: str
    classification_source: str
    diagnostics: tuple[str, ...] = ()


def infer_statement_role_from_pcg_class(pcg_class: int | None) -> str:
    if pcg_class in {1, 4}:
        return "liability"
    if pcg_class in {2, 3, 5}:
        return "asset"
    if pcg_class == 6:
        return "expense"
    if pcg_class == 7:
        return "revenue"
    return "unknown"


def classify_account(account: Any) -> AccountClassification:
    pcg_class = resolved_pcg_class(account)
    statement_role = infer_statement_role_from_pcg_class(pcg_class)
    cash_flow_role = "treasury" if statement_role == "asset" and pcg_class == 5 else "unknown"
    source = "code" if account_code(account) else "unknown"
    return AccountClassification(
        pcg_class=pcg_class,
        statement_role=statement_role,
        cash_flow_role=cash_flow_role,
        classification_source=source,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_accounting_core.py -k "pcg_class or statement_role_uses_pcg_code" -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_accounting_core.py src/FortyFour/accounting/core.py
git commit -m "feat: add canonical code-first account classification"
```

### Task 2: Add optional hierarchy support with ancestor fallback

**Files:**
- Modify: `tests/test_accounting_core.py`
- Modify: `src/FortyFour/accounting/core.py:80-220`

**Step 1: Write the failing test**

```python
def test_classify_account_inherits_role_from_parent_chain() -> None:
    root = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), code="200000", name="Immobilisations", parent_id=None)
    child = SimpleNamespace(id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), code="218100", name="Equipment", parent_id=root.id)
    account_index = {root.id: root, child.id: child}

    classification = classify_account(child, account_index=account_index)

    assert classification.statement_role == "asset"
    assert classification.classification_source == "hierarchy"
```

```python
def test_classify_account_reports_missing_parent_diagnostic() -> None:
    orphan = SimpleNamespace(
        id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        code="401100",
        name="Supplier",
        parent_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
    )

    classification = classify_account(orphan, account_index={orphan.id: orphan})

    assert "missing_parent" in classification.diagnostics
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_accounting_core.py -k "inherits_role_from_parent_chain or missing_parent_diagnostic" -v`

Expected: FAIL because `classify_account` does not yet resolve ancestors or emit hierarchy diagnostics.

**Step 3: Write minimal implementation**

Add defensive hierarchy helpers in `src/FortyFour/accounting/core.py`:

```python
def get_account_parent_id(account: Any) -> UUID | None:
    return get_line_value(account, "parent_id", None)


def resolve_account_ancestry(account: Any, account_index: dict[UUID, Any] | None = None) -> tuple[list[Any], tuple[str, ...]]:
    if not account_index:
        return [], ()

    diagnostics: list[str] = []
    ancestors: list[Any] = []
    seen: set[UUID] = set()
    current_parent_id = get_account_parent_id(account)

    while current_parent_id is not None:
        if current_parent_id in seen:
            diagnostics.append("cycle_detected")
            break
        seen.add(current_parent_id)
        parent = account_index.get(current_parent_id)
        if parent is None:
            diagnostics.append("missing_parent")
            break
        ancestors.append(parent)
        current_parent_id = get_account_parent_id(parent)

    return ancestors, tuple(diagnostics)
```

Then update `classify_account` to prefer the nearest classified ancestor before falling back to the account’s own code.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_accounting_core.py -k "inherits_role_from_parent_chain or missing_parent_diagnostic" -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_accounting_core.py src/FortyFour/accounting/core.py
git commit -m "feat: add optional account hierarchy classification"
```

### Task 3: Refactor income statement and balance sheet grouping to use canonical roles

**Files:**
- Modify: `src/FortyFour/accounting/sqlalchemy_adapter.py:196-330`
- Modify: `src/FortyFour/accounting/core.py:361-423`
- Create: `tests/test_accounting_sqlalchemy_adapter.py`

**Step 1: Write the failing test**

```python
def test_group_posted_lines_exposes_statement_role_from_code(monkeypatch, fake_session):
    rows = _group_posted_lines(fake_session, company_id=UUID("11111111-1111-1111-1111-111111111111"))

    revenue_row = next(row for row in rows if row["account_code"] == "707000")

    assert revenue_row["statement_role"] == "revenue"
```

```python
def test_generate_balance_sheet_does_not_depend_on_account_type(fake_session):
    statement = generate_balance_sheet(fake_session, company_id=UUID("11111111-1111-1111-1111-111111111111"), end_date=datetime(2025, 12, 31, tzinfo=UTC))

    assert any(line["account_code"] == "218100" for line in statement["assets"]["lines"])
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_accounting_sqlalchemy_adapter.py -v`

Expected: FAIL because `_group_posted_lines` does not yet return canonical statement roles and `generate_balance_sheet` still filters on raw `account_type`.

**Step 3: Write minimal implementation**

Query `parent_id` when available and classify grouped rows before returning them:

```python
def _build_account_index(items: list[dict[str, Any]]) -> dict[UUID, Any]:
    return {
        item["account_id"]: SimpleNamespace(
            id=item["account_id"],
            code=item["account_code"],
            name=item["account_name"],
            account_type=item.get("account_type"),
            account_class=item.get("account_class"),
            parent_id=item.get("parent_id"),
        )
        for item in items
    }


def _apply_account_classification(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    account_index = _build_account_index(items)
    for item in items:
        classification = classify_account(account_index[item["account_id"]], account_index=account_index)
        item["statement_role"] = classification.statement_role
        item["cash_flow_role"] = classification.cash_flow_role
        item["classification_source"] = classification.classification_source
        item["classification_diagnostics"] = list(classification.diagnostics)
    return items
```

Then change `generate_income_statement` and `generate_balance_sheet` to build sections from `statement_role` instead of adapter-level `account_type` filters.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_accounting_sqlalchemy_adapter.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_accounting_sqlalchemy_adapter.py src/FortyFour/accounting/sqlalchemy_adapter.py src/FortyFour/accounting/core.py
git commit -m "feat: build statements from canonical account roles"
```

### Task 4: Rework treasury and cash-flow routing around canonical roles

**Files:**
- Modify: `src/FortyFour/accounting/core.py:161-520`
- Modify: `tests/test_accounting_core.py`

**Step 1: Write the failing test**

```python
def test_is_treasury_account_can_use_parent_chain_before_name_markers() -> None:
    treasury_root = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), code="510000", name="Treasury", parent_id=None)
    bank = SimpleNamespace(id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), code="512100", name="Main operating account", parent_id=treasury_root.id)
    account_index = {treasury_root.id: treasury_root, bank.id: bank}

    assert is_treasury_account(bank, account_index=account_index)
```

```python
def test_cash_flow_uses_shared_classifier_for_investing_line() -> None:
    # Existing fixture style, but the counterpart account is a class-2 asset with no investing keyword.
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_accounting_core.py -k "treasury_account_can_use_parent_chain or shared_classifier_for_investing_line" -v`

Expected: FAIL because treasury and investing logic still depends mainly on `account_type` and name markers.

**Step 3: Write minimal implementation**

Update treasury and cash-flow routing signatures to reuse `classify_account` and `account_index`:

```python
def is_treasury_account(
    account: Any | None,
    treasury_account_ids: Iterable[UUID] | None = None,
    account_index: dict[UUID, Any] | None = None,
) -> bool:
    if not account:
        return False
    if normalize_account_ids(treasury_account_ids) and get_line_value(account, "id", None) in normalize_account_ids(treasury_account_ids):
        return True
    classification = classify_account(account, account_index=account_index)
    if classification.cash_flow_role == "treasury":
        return True
    return account_code_matches_prefixes(account, TREASURY_ACCOUNT_CODE_PREFIXES)
```

Refactor `select_counterpart_lines_for_cash_flow` and `build_cash_flow_statement` to pass the same account index through every classification call.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_accounting_core.py -k "treasury_account_can_use_parent_chain or shared_classifier_for_investing_line" -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_accounting_core.py src/FortyFour/accounting/core.py
git commit -m "feat: route cash flow with canonical hierarchy-aware classifier"
```

### Task 5: Add completeness diagnostics and statement reconciliation checks

**Files:**
- Modify: `src/FortyFour/accounting/core.py:325-520`
- Modify: `src/FortyFour/accounting/sqlalchemy_adapter.py:196-451`
- Modify: `tests/test_accounting_core.py`

**Step 1: Write the failing test**

```python
def test_balance_sheet_reports_unclassified_accounts() -> None:
    statement = build_balance_sheet(
        company_id=UUID("11111111-1111-1111-1111-111111111111"),
        end_date=datetime(2025, 12, 31, tzinfo=UTC),
        asset_items=[],
        liability_items=[],
        equity_items=[],
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert "diagnostics" in statement
```

```python
def test_income_statement_carries_classification_diagnostics_forward() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_accounting_core.py -k "diagnostics" -v`

Expected: FAIL because statement builders do not currently expose diagnostic payloads.

**Step 3: Write minimal implementation**

Extend statement payloads to include explicit diagnostics:

```python
def build_balance_sheet(..., diagnostics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ...
    return {
        ...,
        "diagnostics": diagnostics or [],
    }
```

Likewise update `build_income_statement` and `build_cash_flow_statement`, then feed classified-row diagnostics from the adapter into those builders.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_accounting_core.py -k "diagnostics" -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_accounting_core.py src/FortyFour/accounting/core.py src/FortyFour/accounting/sqlalchemy_adapter.py
git commit -m "feat: expose statement completeness diagnostics"
```

### Task 6: Update public docs to describe code-first and hierarchy-aware behavior

**Files:**
- Modify: `src/FortyFour/accounting/README.md`
- Modify: `README.md`

**Step 1: Write the failing documentation check**

Manual check: confirm the docs do not yet mention that `parent_id` is optional and that six-digit PCG codes are the primary fallback classification source.

**Step 2: Run check to verify the gap**

Run: `rg -n "parent_id|six-digit|PCG|classification" src/FortyFour/accounting/README.md README.md`

Expected: Missing or incomplete coverage.

**Step 3: Write minimal documentation update**

Add a short section like:

```markdown
## Classification Rules

Financial statements are generated from a shared classifier.

- `parent_id` ancestry is used first when present.
- Six-digit PCG account codes are used as the primary fallback.
- `account_type` and account names are used only as weak fallbacks.
```

**Step 4: Run check to verify it passes**

Run: `rg -n "parent_id|six-digit|PCG|classification" src/FortyFour/accounting/README.md README.md`

Expected: Matches in both files.

**Step 5: Commit**

```bash
git add src/FortyFour/accounting/README.md README.md
git commit -m "docs: explain hierarchy-aware account classification"
```

### Task 7: Run focused verification before merge

**Files:**
- Test: `tests/test_accounting_core.py`
- Test: `tests/test_accounting_sqlalchemy_adapter.py`

**Step 1: Run core tests**

Run: `pytest tests/test_accounting_core.py -v`

Expected: PASS

**Step 2: Run adapter tests**

Run: `pytest tests/test_accounting_sqlalchemy_adapter.py -v`

Expected: PASS

**Step 3: Run combined accounting tests**

Run: `pytest tests/test_accounting_core.py tests/test_accounting_sqlalchemy_adapter.py tests/test_accounting_module_layout.py -v`

Expected: PASS

**Step 4: Review diff**

Run: `git diff -- src/FortyFour/accounting tests README.md`

Expected: only hierarchy-aware classification and documentation changes.

**Step 5: Commit final verification checkpoint**

```bash
git add src/FortyFour/accounting tests README.md
git commit -m "test: verify hierarchy-aware financial statement generation"
```