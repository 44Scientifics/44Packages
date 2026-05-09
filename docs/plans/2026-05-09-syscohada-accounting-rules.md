# Syscohada Accounting Rules Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a Strategy pattern to accurately support SYSCOHADA accounting rules, including Class 8 (Hors Activités Ordinaires), dynamic Balance Sheet reclassification (e.g., overdrafts becoming liabilities), and accurate Cash Flow mappings.

**Architecture:** Create an `AccountingStrategy` Protocol with a `DefaultStrategy` and a `SyscohadaStrategy`. Refactor the existing reporting logic in `core.py` and `sqlalchemy_adapter.py` to delegate the determination of account roles (`statement_role` and `cash_flow_role`) to the active strategy, evaluating roles based on actual pre-calculated balances.

**Tech Stack:** Python, SQLAlchemy

---

### Task 1: Create AccountingStrategy Protocol and DefaultStrategy

**Files:**
- Create: `src/FortyFour/accounting/strategies/base.py`
- Create: `src/FortyFour/accounting/strategies/__init__.py`
- Create: `tests/accounting/test_strategies.py` (Assuming pytest test directory structure)

**Step 1: Write the failing test**
```python
# tests/accounting/test_strategies.py
import pytest
from decimal import Decimal
from FortyFour.accounting.strategies.base import DefaultStrategy

def test_default_strategy_classifies_asset():
    strategy = DefaultStrategy()
    # Assuming account object with pcg_class=2
    class MockAccount:
        def __init__(self, pcg_class):
            self.account_class = pcg_class
            self.account_type = ""
            self.normal_balance = ""
            self.code = str(pcg_class)
    
    account = MockAccount(2)
    role = strategy.classify_statement_role(account, Decimal("100.00"))
    assert role == "asset"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/accounting/test_strategies.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'FortyFour.accounting.strategies'"

**Step 3: Write minimal implementation**
```python
# src/FortyFour/accounting/strategies/base.py
from typing import Any, Protocol
from decimal import Decimal
from ..core import infer_statement_role_from_pcg_class, classify_cash_flow_account

class AccountingStrategy(Protocol):
    def classify_statement_role(self, account: Any, net_balance: Decimal) -> str:
        ...
    def classify_cash_flow_role(self, account: Any) -> str:
        ...

class DefaultStrategy:
    def classify_statement_role(self, account: Any, net_balance: Decimal) -> str:
        from ..core import resolve_pcg_class_with_source
        pcg_class, _ = resolve_pcg_class_with_source(account)
        return infer_statement_role_from_pcg_class(pcg_class, account)
    
    def classify_cash_flow_role(self, account: Any) -> str:
        return classify_cash_flow_account(account)

# src/FortyFour/accounting/strategies/__init__.py
from .base import AccountingStrategy, DefaultStrategy
__all__ = ["AccountingStrategy", "DefaultStrategy"]
```

**Step 4: Run test to verify it passes**
Run: `pytest tests/accounting/test_strategies.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/FortyFour/accounting/strategies/ tests/accounting/test_strategies.py
git commit -m "feat: add base AccountingStrategy protocol and DefaultStrategy"
```

### Task 2: Implement SyscohadaStrategy

**Files:**
- Create: `src/FortyFour/accounting/strategies/syscohada.py`
- Modify: `src/FortyFour/accounting/strategies/__init__.py`
- Modify: `tests/accounting/test_strategies.py`

**Step 1: Write the failing tests for SYSCOHADA rules**
```python
# append to tests/accounting/test_strategies.py
from FortyFour.accounting.strategies.syscohada import SyscohadaStrategy

def test_syscohada_dynamic_balance():
    strategy = SyscohadaStrategy()
    class MockAccount:
        def __init__(self, code):
            self.code = code
            self.account_class = int(code[0])
            self.account_type = ""
            self.normal_balance = ""
    
    # Class 5 with debit balance is Asset
    acc_bank = MockAccount("521")
    assert strategy.classify_statement_role(acc_bank, Decimal("100.00")) == "asset"
    
    # Class 5 with credit balance (represented as negative net balance here or explicit balance, depending on implementation)
    # We will pass the natural side net_balance. If normal_balance logic applies, let's pass actual debit-credit.
    assert strategy.classify_statement_role(acc_bank, Decimal("-50.00")) == "liability"

def test_syscohada_class_8():
    strategy = SyscohadaStrategy()
    class MockAccount:
        def __init__(self, code):
            self.code = code
            self.account_class = 8
            self.account_type = ""
            self.normal_balance = ""
    
    # 81 is HAO Expense
    acc_expense = MockAccount("81")
    assert strategy.classify_statement_role(acc_expense, Decimal("0.00")) == "expense"
    
    # 82 is HAO Revenue
    acc_revenue = MockAccount("82")
    assert strategy.classify_statement_role(acc_revenue, Decimal("0.00")) == "revenue"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/accounting/test_strategies.py::test_syscohada_dynamic_balance -v`
Expected: FAIL with "ImportError: cannot import name 'SyscohadaStrategy'"

**Step 3: Write minimal implementation**
```python
# src/FortyFour/accounting/strategies/syscohada.py
from typing import Any
from decimal import Decimal
from .base import DefaultStrategy
from ..core import resolve_pcg_class_with_source, account_code

class SyscohadaStrategy(DefaultStrategy):
    def classify_statement_role(self, account: Any, net_balance: Decimal) -> str:
        pcg_class, _ = resolve_pcg_class_with_source(account)
        code = account_code(account)
        
        # Class 8: Even is revenue, Odd is expense
        if pcg_class == 8 and len(code) >= 2:
            try:
                sub_class = int(code[0:2])
                if sub_class % 2 == 0:
                    return "revenue"
                else:
                    return "expense"
            except ValueError:
                pass
                
        # Dynamic reclassification for Class 4 and 5 based on actual balance (Debit - Credit)
        if pcg_class in (4, 5):
            # net_balance is expected to be (debit - credit) in this context
            if net_balance < Decimal("0.00"):
                return "liability"
            else:
                return "asset"
                
        # Fallback to default
        return super().classify_statement_role(account, net_balance)
```

**Step 4: Run test to verify it passes**
Run: `pytest tests/accounting/test_strategies.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/FortyFour/accounting/strategies/syscohada.py src/FortyFour/accounting/strategies/__init__.py tests/accounting/test_strategies.py
git commit -m "feat: implement SyscohadaStrategy with Class 8 and dynamic reclassification rules"
```

### Task 3: Refactor core.py and sqlalchemy_adapter.py to use Strategy

**Files:**
- Modify: `src/FortyFour/accounting/core.py`
- Modify: `src/FortyFour/accounting/sqlalchemy_adapter.py`

**Step 1: Write the failing tests (Update existing report tests to inject strategy)**
*(Since this is a refactor of the report generation, we expect existing tests to pass or fail depending on how strictly they relied on the old behavior. We will ensure the tests pass with the injected strategy.)*

**Step 2: Run test to verify**
Run: `pytest tests/accounting/ -v`

**Step 3: Write minimal implementation**
1. Modify `sqlalchemy_adapter.py`: `_group_posted_lines` to accept `strategy: AccountingStrategy = None` and compute `net_balance = debit - credit` *before* classification.
2. Replace `classify_account` logic in `_group_posted_lines` to use `strategy.classify_statement_role(account, debit - credit)`.
3. Ensure `build_balance_sheet`, `generate_trial_balance`, etc. accept `strategy` kwargs and pass them down.

**Step 4: Run test to verify it passes**
Run: `pytest tests/accounting/ -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/FortyFour/accounting/core.py src/FortyFour/accounting/sqlalchemy_adapter.py
git commit -m "refactor: inject AccountingStrategy into statement generation for dynamic rules"
```
