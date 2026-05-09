import os
import sys
import importlib
from uuid import UUID

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


def test_accounting_engine_module_is_available_under_accounting_package() -> None:
    from FortyFour.accounting import engine

    assert callable(engine.generate_trial_balance)
    assert callable(engine.generate_cash_flow_statement)
    assert callable(engine.validate_journal_entry_lines)


def test_accounting_package_exports_public_engine_api_directly() -> None:
    from FortyFour.accounting import (
        generate_balance_sheet,
        generate_cash_flow_statement,
        generate_income_statement,
        generate_trial_balance,
        validate_journal_entry_lines,
    )

    assert callable(generate_balance_sheet)
    assert callable(generate_cash_flow_statement)
    assert callable(generate_income_statement)
    assert callable(generate_trial_balance)
    assert callable(validate_journal_entry_lines)


def test_finance_accounting_engine_module_is_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("FortyFour.Finance.accounting_engine")


def test_accounting_engine_forwards_strategy_to_adapter(monkeypatch) -> None:
    from FortyFour.accounting import engine
    from FortyFour.accounting import sqlalchemy_adapter
    from FortyFour.accounting.strategies import SyscohadaStrategy

    expected = {"statement": "ok"}
    captured = {}

    def fake_generate_trial_balance(
        db,
        company_id,
        start_date=None,
        end_date=None,
        strategy=None,
    ):
        captured["company_id"] = company_id
        captured["strategy"] = strategy
        return expected

    monkeypatch.setattr(sqlalchemy_adapter, "generate_trial_balance", fake_generate_trial_balance)

    strategy = SyscohadaStrategy()
    statement = engine.generate_trial_balance(
        db=object(),
        company_id=UUID("99999999-9999-9999-9999-999999999999"),
        strategy=strategy,
    )

    assert statement == expected
    assert captured["company_id"] == UUID("99999999-9999-9999-9999-999999999999")
    assert captured["strategy"] is strategy
