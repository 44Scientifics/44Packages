import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from FortyFour import models as ff_models
from FortyFour.accounting import generate_trial_balance

Base = declarative_base()


class ChartOfAccountModel(Base):
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    account_type = Column(String, nullable=False)
    account_class = Column(Integer, nullable=True)
    normal_balance = Column(String, nullable=True)
    account_owner = Column(Uuid, nullable=True)
    parent_id = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)


class JournalEntryModel(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    company_id = Column(Uuid, nullable=True)
    date = Column(DateTime, nullable=False)
    status = Column(String, default="posted")
    currency = Column(String, nullable=True)
    lines = relationship("JournalEntryLineModel", back_populates="entry")


class JournalEntryLineModel(Base):
    __tablename__ = "journal_entry_lines"

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("journal_entries.id"))
    account_id = Column(Integer, ForeignKey("chart_of_accounts.id"))
    debit = Column(Integer, default=0)
    credit = Column(Integer, default=0)
    entry = relationship("JournalEntryModel", back_populates="lines")
    account = relationship("ChartOfAccountModel")


@pytest.fixture(scope="module", autouse=True)
def configure_models():
    ff_models.configure(
        chart_of_account=ChartOfAccountModel,
        journal_entry=JournalEntryModel,
        journal_entry_line=JournalEntryLineModel,
        journal_entry_attachment=None,
        journal_entry_status=None,
    )


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def seed_accounts(db, owner: UUID | None, count: int = 4):
    accounts = []
    for index in range(1, count + 1):
        account = ChartOfAccountModel(
            id=index,
            code=f"{index}00",
            name=f"Account {index}",
            account_type=["asset", "liability", "equity", "revenue"][index - 1],
            account_class=index,
            account_owner=owner,
        )
        db.add(account)
        accounts.append(account)
    db.flush()
    return accounts


def seed_entry(db, date, currency, lines, company_id=None, status="posted"):
    entry = JournalEntryModel(company_id=company_id, date=date, status=status, currency=currency)
    db.add(entry)
    db.flush()
    for account_id, debit, credit in lines:
        db.add(
            JournalEntryLineModel(
                entry_id=entry.id,
                account_id=account_id,
                debit=debit,
                credit=credit,
            )
        )
    db.flush()
    return entry


def test_trial_balance_filters_by_currency(db) -> None:
    owner = uuid4()
    accounts = seed_accounts(db, owner)
    today = datetime.now(UTC)
    seed_entry(db, today, "EUR", [(accounts[0].id, 100, 0)], company_id=owner)
    seed_entry(db, today, "XOF", [(accounts[0].id, 50, 0)], company_id=owner)
    db.commit()

    statement = generate_trial_balance(db, owner, currency="EUR")

    assert statement["currency"] == "EUR"
    assert statement["total_debit"] == Decimal("100.00")
    assert statement["total_credit"] == Decimal("0.00")


def test_trial_balance_aggregates_all_currencies_without_filter(db) -> None:
    owner = uuid4()
    accounts = seed_accounts(db, owner)
    today = datetime.now(UTC)
    seed_entry(db, today, "EUR", [(accounts[0].id, 100, 0)], company_id=owner)
    seed_entry(db, today, "XOF", [(accounts[0].id, 50, 0)], company_id=owner)
    db.commit()

    statement = generate_trial_balance(db, owner)

    assert statement["currency"] is None
    assert statement["total_debit"] == Decimal("150.00")


def test_trial_balance_excludes_draft_entries(db) -> None:
    owner = uuid4()
    accounts = seed_accounts(db, owner)
    today = datetime.now(UTC)
    seed_entry(db, today, "EUR", [(accounts[0].id, 100, 0)], company_id=owner, status="draft")
    seed_entry(db, today, "EUR", [(accounts[0].id, 25, 0)], company_id=owner)
    db.commit()

    statement = generate_trial_balance(db, owner)

    assert statement["total_debit"] == Decimal("25.00")


def test_grouped_items_include_opening_and_closing_balances(db) -> None:
    owner = uuid4()
    accounts = seed_accounts(db, owner)
    today = datetime.now(UTC)
    before = today - timedelta(days=30)
    seed_entry(db, before, "EUR", [(accounts[0].id, 100, 0)], company_id=owner)
    seed_entry(db, today, "EUR", [(accounts[0].id, 50, 0)], company_id=owner)
    db.commit()

    statement = generate_trial_balance(
        db,
        owner,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=1),
    )

    cash_item = next(item for item in statement["items"] if item["account_code"] == "100")
    assert cash_item["opening_balance"] == Decimal("100.00")
    assert cash_item["closing_balance"] == Decimal("150.00")


def test_trial_balance_without_company_id_aggregates_all_owners(db) -> None:
    accounts = seed_accounts(db, owner=None)
    today = datetime.now(UTC)
    seed_entry(db, today, "EUR", [(accounts[0].id, 70, 0)], company_id=None)
    db.commit()

    statement = generate_trial_balance(db, None)

    assert statement["total_debit"] == Decimal("70.00")
