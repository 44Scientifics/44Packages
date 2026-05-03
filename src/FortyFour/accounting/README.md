# FortyFour Accounting

Reusable accounting primitives and SQLAlchemy-backed reporting helpers.

This package is split into three layers:

- `FortyFour.accounting.core`: pure accounting logic, snapshot dataclasses, and statement builders.
- `FortyFour.accounting.sqlalchemy_adapter`: SQLAlchemy adapter layer for ORM-backed projects.
- `FortyFour.accounting.engine`: public facade for the accounting API.

The old `FortyFour.Finance.accounting_engine` path has been removed. Use `FortyFour.accounting` directly.

## Installation

From another project, install the built wheel, install directly from GitHub, or use an editable local install while developing:

```bash
# Build the package first
cd /path/to/44Packages
./build.sh

# Install the generated wheel into another project
pip install /path/to/44Packages/dist/fortyfour-2026.4.29-py3-none-any.whl

# Install directly from the remote Git repository
pip install "git+https://github.com/44Scientifics/44Packages.git@main"

# Or, while working locally, install the source tree in editable mode
pip install -e /path/to/44Packages
```

If you prefer a pinned revision, replace `main` with a tag or commit SHA.

After installation, import the module with `FortyFour.accounting`.

## Quick Start

For most users, import the public API directly from the package root:

```python
from FortyFour.accounting import generate_trial_balance, generate_cash_flow_statement

trial_balance = generate_trial_balance(db, company_id)
cash_flow = generate_cash_flow_statement(db, company_id)
```

If you want the explicit facade module, import `engine`:

```python
from FortyFour.accounting import engine

trial_balance = engine.generate_trial_balance(db, company_id)
income_statement = engine.generate_income_statement(db, company_id)
balance_sheet = engine.generate_balance_sheet(db, company_id, end_date)
```

If you only need the pure business logic, use the core module directly:

```python
from decimal import Decimal
from uuid import UUID

from FortyFour.accounting.core import (
    AccountSnapshot,
    EntryLineSnapshot,
    JournalEntrySnapshot,
    build_cash_flow_statement,
    validate_journal_entry_lines,
)

cash = AccountSnapshot(
    id=UUID("11111111-1111-1111-1111-111111111111"),
    code="512",
    name="Main bank",
    account_type="asset",
    account_class=5,
    normal_balance="debit",
)

sales = AccountSnapshot(
    id=UUID("22222222-2222-2222-2222-222222222222"),
    code="701",
    name="Sales",
    account_type="revenue",
    account_class=7,
    normal_balance="credit",
)

lines = [
    EntryLineSnapshot(account_id=cash.id, account=cash, debit=Decimal("100.00")),
    EntryLineSnapshot(account_id=sales.id, account=sales, credit=Decimal("100.00")),
]

validate_journal_entry_lines(lines)

statement = build_cash_flow_statement(
    company_id=UUID("33333333-3333-3333-3333-333333333333"),
    entries=[JournalEntrySnapshot(lines=tuple(lines))],
    closing_cash_balance=Decimal("100.00"),
)
```

## Public API

Root package exports:

- `engine`
- `AccountSnapshot`
- `EntryLineSnapshot`
- `JournalEntrySnapshot`
- `generate_trial_balance`
- `generate_income_statement`
- `generate_balance_sheet`
- `generate_cash_flow_statement`
- `get_account_balance`
- `validate_journal_entry_lines`

## Notes

- The core module does not depend on SQLAlchemy.
- The SQLAlchemy adapter expects ORM models compatible with the `ChartOfAccount`, `JournalEntry`, and `JournalEntryLine` shape used by FortyFour.
- The package-level API is intended to stay stable while internals are refactored.