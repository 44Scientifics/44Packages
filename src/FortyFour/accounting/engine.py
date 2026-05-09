from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Sequence
from uuid import UUID

from .core import validate_journal_entry_lines


if TYPE_CHECKING:
    from .strategies import AccountingStrategy


def assert_company_owns_accounts(db: Any, company_id: UUID, lines: Sequence):
    from .sqlalchemy_adapter import assert_company_owns_accounts as _impl

    return _impl(db, company_id, lines)


def get_account_balance(
    db: Any,
    account_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    include_children: bool = True,
) -> Decimal:
    from .sqlalchemy_adapter import get_account_balance as _impl

    return _impl(
        db,
        account_id,
        start_date=start_date,
        end_date=end_date,
        include_children=include_children,
    )


def generate_trial_balance(
    db: Any,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    strategy: AccountingStrategy | None = None,
):
    from .sqlalchemy_adapter import generate_trial_balance as _impl

    return _impl(db, company_id, start_date=start_date, end_date=end_date, strategy=strategy)


def generate_income_statement(
    db: Any,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    strategy: AccountingStrategy | None = None,
):
    from .sqlalchemy_adapter import generate_income_statement as _impl

    return _impl(db, company_id, start_date=start_date, end_date=end_date, strategy=strategy)


def generate_balance_sheet(
    db: Any,
    company_id: UUID,
    end_date: datetime,
    strategy: AccountingStrategy | None = None,
):
    from .sqlalchemy_adapter import generate_balance_sheet as _impl

    return _impl(db, company_id, end_date=end_date, strategy=strategy)


def generate_cash_flow_statement(
    db: Any,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    treasury_account_ids: Sequence[UUID] | None = None,
    investing_account_ids: Sequence[UUID] | None = None,
    financing_account_ids: Sequence[UUID] | None = None,
    strategy: AccountingStrategy | None = None,
):
    from .sqlalchemy_adapter import generate_cash_flow_statement as _impl

    return _impl(
        db,
        company_id,
        start_date=start_date,
        end_date=end_date,
        treasury_account_ids=treasury_account_ids,
        investing_account_ids=investing_account_ids,
        financing_account_ids=financing_account_ids,
        strategy=strategy,
    )


__all__ = [
    "assert_company_owns_accounts",
    "generate_balance_sheet",
    "generate_cash_flow_statement",
    "generate_income_statement",
    "generate_trial_balance",
    "get_account_balance",
    "validate_journal_entry_lines",
]