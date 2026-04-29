from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .. import models
from .core import (
    AccountSnapshot,
    EntryLineSnapshot,
    JournalEntrySnapshot,
    ZERO,
    build_balance_sheet,
    build_cash_flow_statement,
    build_income_statement,
    build_trial_balance,
    get_line_value,
    is_treasury_account,
    normalize_account_ids,
    to_decimal,
)


def _to_account_snapshot(account: models.ChartOfAccount) -> AccountSnapshot:
    return AccountSnapshot(
        id=account.id,
        code=str(account.code or ""),
        name=str(account.name or ""),
        description=str(getattr(account, "description", "") or ""),
        account_type=str(account.account_type or ""),
        account_class=getattr(account, "account_class", None),
        normal_balance=getattr(account, "normal_balance", None),
    )


def _to_entry_line_snapshot(line: models.JournalEntryLine) -> EntryLineSnapshot:
    return EntryLineSnapshot(
        account_id=line.account_id,
        account=_to_account_snapshot(line.account),
        debit=to_decimal(line.debit),
        credit=to_decimal(line.credit),
    )


def _to_journal_entry_snapshot(entry: models.JournalEntry) -> JournalEntrySnapshot:
    return JournalEntrySnapshot(lines=tuple(_to_entry_line_snapshot(line) for line in entry.lines))


def _validate_cash_flow_overrides(
    db: Session,
    company_id: UUID,
    treasury_account_ids: set[UUID],
    investing_account_ids: set[UUID],
    financing_account_ids: set[UUID],
) -> None:
    overlaps = [
        treasury_account_ids & investing_account_ids,
        treasury_account_ids & financing_account_ids,
        investing_account_ids & financing_account_ids,
    ]
    overlapping_ids = set().union(*overlaps)
    if overlapping_ids:
        raise ValueError("Cash flow override accounts cannot belong to multiple classification roles")

    override_account_ids = treasury_account_ids | investing_account_ids | financing_account_ids
    if not override_account_ids:
        return

    accounts = (
        db.query(models.ChartOfAccount)
        .filter(models.ChartOfAccount.id.in_(override_account_ids))
        .all()
    )
    accounts_by_id = {account.id: account for account in accounts}

    for account_id in override_account_ids:
        account = accounts_by_id.get(account_id)
        if not account:
            raise ValueError(f"Cash flow override account not found: {account_id}")
        if account.account_owner and account.account_owner != company_id:
            raise ValueError(
                (
                    f"Ownership mismatch: Account '{account.code} - {account.name}' "
                    f"(ID: {account.id}) is owned by company '{account.account_owner}', "
                    f"but the cash flow statement belongs to '{company_id}'."
                )
            )


def assert_company_owns_accounts(
    db: Session,
    company_id: UUID,
    lines: Sequence,
) -> dict[UUID, models.ChartOfAccount]:
    account_ids = []
    for line in lines:
        account_id = get_line_value(line, "account_id")
        if account_id not in account_ids:
            account_ids.append(account_id)

    accounts = (
        db.query(models.ChartOfAccount)
        .filter(models.ChartOfAccount.id.in_(account_ids))
        .all()
    )
    accounts_by_id = {account.id: account for account in accounts}

    for account_id in account_ids:
        account = accounts_by_id.get(account_id)
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        if not account.is_active:
            raise ValueError(f"Account '{account.code} - {account.name}' is inactive")
        if account.account_owner and account.account_owner != company_id:
            raise ValueError(
                (
                    f"Ownership mismatch: Account '{account.code} - {account.name}' "
                    f"(ID: {account.id}) is owned by company '{account.account_owner}', "
                    f"but the journal entry belongs to '{company_id}'. The initiator must be the account owner."
                )
            )

    return accounts_by_id


def _build_line_query(
    db: Session,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    query = (
        db.query(models.JournalEntryLine)
        .join(models.JournalEntry)
        .filter(models.JournalEntry.company_id == company_id)
        .filter(models.JournalEntry.status == "posted")
    )

    if start_date:
        query = query.filter(models.JournalEntry.date >= start_date)
    if end_date:
        query = query.filter(models.JournalEntry.date <= end_date)

    return query


def get_account_balance(
    db: Session,
    account_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    include_children: bool = True,
):
    account = db.query(models.ChartOfAccount).filter(models.ChartOfAccount.id == account_id).first()
    if not account:
        raise ValueError(f"Account not found: {account_id}")

    account_ids = [account_id]
    if include_children:
        pending = [account_id]
        while pending:
            current_id = pending.pop()
            child_ids = [
                child_id
                for (child_id,) in db.query(models.ChartOfAccount.id)
                .filter(models.ChartOfAccount.parent_id == current_id)
                .all()
            ]
            for child_id in child_ids:
                if child_id not in account_ids:
                    account_ids.append(child_id)
                    pending.append(child_id)

    totals = (
        _build_line_query(db, company_id=account.account_owner, start_date=start_date, end_date=end_date)
        .with_entities(
            func.coalesce(func.sum(models.JournalEntryLine.debit), 0),
            func.coalesce(func.sum(models.JournalEntryLine.credit), 0),
        )
        .filter(models.JournalEntryLine.account_id.in_(account_ids))
        .one()
    )
    debit_total = to_decimal(totals[0])
    credit_total = to_decimal(totals[1])
    if account.normal_balance == "credit":
        return credit_total - debit_total
    return debit_total - credit_total


def _group_posted_lines(
    db: Session,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    account_types: Iterable[str] | None = None,
):
    query = (
        _build_line_query(db, company_id=company_id, start_date=start_date, end_date=end_date)
        .join(models.ChartOfAccount, models.ChartOfAccount.id == models.JournalEntryLine.account_id)
    )
    if account_types:
        query = query.filter(models.ChartOfAccount.account_type.in_(list(account_types)))

    rows = (
        query.with_entities(
            models.ChartOfAccount.id,
            models.ChartOfAccount.code,
            models.ChartOfAccount.name,
            models.ChartOfAccount.account_type,
            models.ChartOfAccount.account_class,
            models.ChartOfAccount.normal_balance,
            func.coalesce(func.sum(models.JournalEntryLine.debit), 0),
            func.coalesce(func.sum(models.JournalEntryLine.credit), 0),
        )
        .group_by(
            models.ChartOfAccount.id,
            models.ChartOfAccount.code,
            models.ChartOfAccount.name,
            models.ChartOfAccount.account_type,
            models.ChartOfAccount.account_class,
            models.ChartOfAccount.normal_balance,
        )
        .order_by(models.ChartOfAccount.code.asc())
        .all()
    )

    items = []
    for row in rows:
        debit = to_decimal(row[6])
        credit = to_decimal(row[7])
        normal_balance = row[5]
        net_balance = credit - debit if normal_balance == "credit" else debit - credit
        items.append(
            {
                "account_id": row[0],
                "account_code": row[1],
                "account_name": row[2],
                "account_type": row[3],
                "account_class": row[4],
                "normal_balance": normal_balance,
                "debit": debit,
                "credit": credit,
                "net_balance": net_balance,
            }
        )
    return items


def generate_trial_balance(
    db: Session,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    items = _group_posted_lines(db, company_id=company_id, start_date=start_date, end_date=end_date)
    return build_trial_balance(
        company_id=company_id,
        items=items,
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.now(timezone.utc),
    )


def generate_income_statement(
    db: Session,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    revenue_items = _group_posted_lines(
        db,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        account_types=("revenue", "income"),
    )
    expense_items = _group_posted_lines(
        db,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        account_types=("expense",),
    )
    return build_income_statement(
        company_id=company_id,
        revenue_items=revenue_items,
        expense_items=expense_items,
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.now(timezone.utc),
    )


def generate_balance_sheet(db: Session, company_id: UUID, end_date: datetime):
    asset_items = _group_posted_lines(
        db,
        company_id=company_id,
        end_date=end_date,
        account_types=("asset",),
    )
    liability_items = _group_posted_lines(
        db,
        company_id=company_id,
        end_date=end_date,
        account_types=("liability",),
    )
    equity_items = _group_posted_lines(
        db,
        company_id=company_id,
        end_date=end_date,
        account_types=("equity",),
    )

    income_statement = generate_income_statement(db, company_id=company_id, end_date=end_date)
    return build_balance_sheet(
        company_id=company_id,
        end_date=end_date,
        asset_items=asset_items,
        liability_items=liability_items,
        equity_items=equity_items,
        net_income=income_statement["net_income"],
        generated_at=datetime.now(timezone.utc),
    )


def _get_posted_entries_with_lines(
    db: Session,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    query = (
        db.query(models.JournalEntry)
        .options(joinedload(models.JournalEntry.lines).joinedload(models.JournalEntryLine.account))
        .filter(models.JournalEntry.company_id == company_id)
        .filter(models.JournalEntry.status == "posted")
    )

    if start_date:
        query = query.filter(models.JournalEntry.date >= start_date)
    if end_date:
        query = query.filter(models.JournalEntry.date <= end_date)

    return query.order_by(models.JournalEntry.date.asc(), models.JournalEntry.id.asc()).all()


def _get_treasury_balance(
    db: Session,
    company_id: UUID,
    end_date: datetime | None = None,
    treasury_account_ids: set[UUID] | None = None,
):
    rows = (
        _build_line_query(db, company_id=company_id, end_date=end_date)
        .join(models.ChartOfAccount, models.ChartOfAccount.id == models.JournalEntryLine.account_id)
        .with_entities(
            models.ChartOfAccount.id,
            models.ChartOfAccount.code,
            models.ChartOfAccount.name,
            models.ChartOfAccount.description,
            models.ChartOfAccount.account_type,
            models.ChartOfAccount.account_class,
            func.coalesce(func.sum(models.JournalEntryLine.debit), 0),
            func.coalesce(func.sum(models.JournalEntryLine.credit), 0),
        )
        .group_by(
            models.ChartOfAccount.id,
            models.ChartOfAccount.code,
            models.ChartOfAccount.name,
            models.ChartOfAccount.description,
            models.ChartOfAccount.account_type,
            models.ChartOfAccount.account_class,
        )
        .all()
    )

    balance = ZERO
    for row in rows:
        account = AccountSnapshot(
            id=row[0],
            code=str(row[1] or ""),
            name=str(row[2] or ""),
            description=str(row[3] or ""),
            account_type=str(row[4] or ""),
            account_class=row[5],
        )
        if not is_treasury_account(account, treasury_account_ids):
            continue
        balance += to_decimal(row[6]) - to_decimal(row[7])

    return to_decimal(balance)


def generate_cash_flow_statement(
    db: Session,
    company_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    treasury_account_ids: Sequence[UUID] | None = None,
    investing_account_ids: Sequence[UUID] | None = None,
    financing_account_ids: Sequence[UUID] | None = None,
):
    treasury_account_id_set = normalize_account_ids(treasury_account_ids)
    investing_account_id_set = normalize_account_ids(investing_account_ids)
    financing_account_id_set = normalize_account_ids(financing_account_ids)
    _validate_cash_flow_overrides(
        db,
        company_id,
        treasury_account_id_set,
        investing_account_id_set,
        financing_account_id_set,
    )
    closing_cash_balance = _get_treasury_balance(
        db,
        company_id=company_id,
        end_date=end_date,
        treasury_account_ids=treasury_account_id_set,
    )
    return build_cash_flow_statement(
        company_id=company_id,
        entries=[
            _to_journal_entry_snapshot(entry)
            for entry in _get_posted_entries_with_lines(
                db,
                company_id=company_id,
                start_date=start_date,
                end_date=end_date,
            )
        ],
        closing_cash_balance=closing_cash_balance,
        start_date=start_date,
        end_date=end_date,
        treasury_account_ids=treasury_account_id_set,
        investing_account_ids=investing_account_id_set,
        financing_account_ids=financing_account_id_set,
        generated_at=datetime.now(timezone.utc),
    )


__all__ = [
    "assert_company_owns_accounts",
    "generate_balance_sheet",
    "generate_cash_flow_statement",
    "generate_income_statement",
    "generate_trial_balance",
    "get_account_balance",
]