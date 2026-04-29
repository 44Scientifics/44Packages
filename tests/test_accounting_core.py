import os
import sys
from datetime import datetime, UTC
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from FortyFour.accounting.core import (
    AccountSnapshot,
    build_balance_sheet,
    build_cash_flow_statement,
    build_income_statement,
    build_trial_balance,
    EntryLineSnapshot,
    JournalEntrySnapshot,
    statement_section,
    validate_journal_entry_lines,
)


def make_account(
    account_id: str,
    code: str,
    name: str,
    account_type: str,
    account_class: int | None = None,
    description: str = "",
):
    return SimpleNamespace(
        id=UUID(account_id),
        code=code,
        name=name,
        description=description,
        account_type=account_type,
        account_class=account_class,
    )


def make_line(account, debit: str = "0.00", credit: str = "0.00"):
    return SimpleNamespace(
        account_id=account.id,
        account=account,
        debit=Decimal(debit),
        credit=Decimal(credit),
    )


def test_validate_journal_entry_lines_accepts_balanced_lines() -> None:
    lines = [
        {"account_id": "cash", "debit": "100.00", "credit": "0.00"},
        {"account_id": "revenue", "debit": "0.00", "credit": "100.00"},
    ]

    validate_journal_entry_lines(lines)


def test_statement_section_ignores_zero_amounts_and_sorts_lines() -> None:
    items = [
        {
            "account_id": "2",
            "account_code": "701",
            "account_name": "Sales",
            "net_balance": Decimal("125.00"),
        },
        {
            "account_id": "1",
            "account_code": "512",
            "account_name": "Bank",
            "net_balance": Decimal("0.00"),
        },
        {
            "account_id": "3",
            "account_code": "512",
            "account_name": "Secondary bank",
            "net_balance": Decimal("25.00"),
        },
    ]

    section = statement_section("Test", items)

    assert section["title"] == "Test"
    assert section["total"] == Decimal("150.00")
    assert [line["account_name"] for line in section["lines"]] == ["Secondary bank", "Sales"]


def test_build_trial_balance_returns_totals_from_grouped_items() -> None:
    company_id = UUID("11111111-1111-1111-1111-111111111111")
    start_date = datetime(2025, 1, 1, tzinfo=UTC)
    end_date = datetime(2025, 12, 31, tzinfo=UTC)
    generated_at = datetime(2026, 1, 15, tzinfo=UTC)
    items = [
        {"account_code": "512", "debit": Decimal("100.00"), "credit": Decimal("0.00")},
        {"account_code": "701", "debit": Decimal("0.00"), "credit": Decimal("100.00")},
    ]

    statement = build_trial_balance(
        company_id=company_id,
        items=items,
        start_date=start_date,
        end_date=end_date,
        generated_at=generated_at,
    )

    assert statement["company_id"] == company_id
    assert statement["start_date"] == start_date
    assert statement["end_date"] == end_date
    assert statement["total_debit"] == Decimal("100.00")
    assert statement["total_credit"] == Decimal("100.00")
    assert statement["generated_at"] == generated_at


def test_build_income_statement_computes_net_income() -> None:
    company_id = UUID("22222222-2222-2222-2222-222222222222")
    end_date = datetime(2025, 12, 31, tzinfo=UTC)
    generated_at = datetime(2026, 1, 15, tzinfo=UTC)
    revenue_items = [
        {
            "account_id": "rev-1",
            "account_code": "701",
            "account_name": "Sales",
            "net_balance": Decimal("500.00"),
        }
    ]
    expense_items = [
        {
            "account_id": "exp-1",
            "account_code": "601",
            "account_name": "Purchases",
            "net_balance": Decimal("300.00"),
        }
    ]

    statement = build_income_statement(
        company_id=company_id,
        revenue_items=revenue_items,
        expense_items=expense_items,
        end_date=end_date,
        generated_at=generated_at,
    )

    assert statement["total_revenue"] == Decimal("500.00")
    assert statement["total_expenses"] == Decimal("300.00")
    assert statement["net_income"] == Decimal("200.00")
    assert statement["generated_at"] == generated_at


def test_build_balance_sheet_adds_current_period_result_to_equity() -> None:
    company_id = UUID("33333333-3333-3333-3333-333333333333")
    end_date = datetime(2025, 12, 31, tzinfo=UTC)
    generated_at = datetime(2026, 1, 15, tzinfo=UTC)
    asset_items = [
        {
            "account_id": "asset-1",
            "account_code": "512",
            "account_name": "Bank",
            "net_balance": Decimal("1000.00"),
        }
    ]
    liability_items = [
        {
            "account_id": "liab-1",
            "account_code": "401",
            "account_name": "Suppliers",
            "net_balance": Decimal("600.00"),
        }
    ]
    equity_items = [
        {
            "account_id": "eq-1",
            "account_code": "101",
            "account_name": "Capital",
            "net_balance": Decimal("200.00"),
        }
    ]

    statement = build_balance_sheet(
        company_id=company_id,
        end_date=end_date,
        asset_items=asset_items,
        liability_items=liability_items,
        equity_items=equity_items,
        net_income=Decimal("200.00"),
        generated_at=generated_at,
    )

    assert statement["total_assets"] == Decimal("1000.00")
    assert statement["total_liabilities_and_equity"] == Decimal("1000.00")
    assert statement["equity"]["total"] == Decimal("400.00")
    assert statement["equity"]["lines"][-1]["account_code"] == "RESULT"
    assert statement["equity"]["lines"][-1]["amount"] == Decimal("200.00")
    assert statement["generated_at"] == generated_at


def test_build_cash_flow_statement_classifies_simple_receipt_as_operating() -> None:
    company_id = UUID("44444444-4444-4444-4444-444444444444")
    start_date = datetime(2025, 1, 1, tzinfo=UTC)
    end_date = datetime(2025, 12, 31, tzinfo=UTC)
    generated_at = datetime(2026, 1, 15, tzinfo=UTC)

    treasury = make_account(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        code="512",
        name="Main bank",
        account_type="asset",
        account_class=5,
    )
    revenue = make_account(
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        code="701",
        name="Sales",
        account_type="revenue",
        account_class=7,
    )
    entries = [
        SimpleNamespace(
            lines=[
                make_line(treasury, debit="100.00"),
                make_line(revenue, credit="100.00"),
            ]
        )
    ]

    statement = build_cash_flow_statement(
        company_id=company_id,
        entries=entries,
        closing_cash_balance=Decimal("100.00"),
        start_date=start_date,
        end_date=end_date,
        generated_at=generated_at,
    )

    assert statement["operating_activities"]["total"] == Decimal("100.00")
    assert statement["investing_activities"]["total"] == Decimal("0.00")
    assert statement["financing_activities"]["total"] == Decimal("0.00")
    assert statement["net_change_in_cash"] == Decimal("100.00")
    assert statement["opening_cash_balance"] == Decimal("0.00")
    assert statement["closing_cash_balance"] == Decimal("100.00")
    assert statement["operating_activities"]["lines"][0]["account_code"] == "701"


def test_build_cash_flow_statement_routes_asset_disposal_gain_to_investing_only() -> None:
    company_id = UUID("55555555-5555-5555-5555-555555555555")
    generated_at = datetime(2026, 1, 15, tzinfo=UTC)

    treasury = make_account(
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
        code="512",
        name="Main bank",
        account_type="asset",
        account_class=5,
    )
    equipment = make_account(
        "dddddddd-dddd-dddd-dddd-dddddddddddd",
        code="218",
        name="Equipment",
        account_type="asset",
        account_class=2,
    )
    disposal_gain = make_account(
        "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        code="775",
        name="Gain on disposal",
        account_type="revenue",
        account_class=7,
    )
    entries = [
        SimpleNamespace(
            lines=[
                make_line(treasury, debit="120.00"),
                make_line(equipment, credit="100.00"),
                make_line(disposal_gain, credit="20.00"),
            ]
        )
    ]

    statement = build_cash_flow_statement(
        company_id=company_id,
        entries=entries,
        closing_cash_balance=Decimal("120.00"),
        generated_at=generated_at,
    )

    assert statement["operating_activities"]["total"] == Decimal("0.00")
    assert statement["investing_activities"]["total"] == Decimal("120.00")
    assert statement["investing_activities"]["lines"][0]["account_code"] == "218"
    assert statement["net_change_in_cash"] == Decimal("120.00")


def test_snapshot_dataclasses_work_with_validation_and_cash_flow_builder() -> None:
    company_id = UUID("66666666-6666-6666-6666-666666666666")
    treasury = AccountSnapshot(
        id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        code="512",
        name="Main bank",
        account_type="asset",
        account_class=5,
        normal_balance="debit",
    )
    revenue = AccountSnapshot(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        code="701",
        name="Sales",
        account_type="revenue",
        account_class=7,
        normal_balance="credit",
    )
    lines = [
        EntryLineSnapshot(account_id=treasury.id, account=treasury, debit=Decimal("80.00"), credit=Decimal("0.00")),
        EntryLineSnapshot(account_id=revenue.id, account=revenue, debit=Decimal("0.00"), credit=Decimal("80.00")),
    ]

    validate_journal_entry_lines(lines)
    statement = build_cash_flow_statement(
        company_id=company_id,
        entries=[JournalEntrySnapshot(lines=lines)],
        closing_cash_balance=Decimal("80.00"),
    )

    assert statement["operating_activities"]["total"] == Decimal("80.00")
    assert statement["closing_cash_balance"] == Decimal("80.00")
