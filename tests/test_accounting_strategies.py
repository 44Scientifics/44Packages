import os
import sys
from decimal import Decimal


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from FortyFour.accounting.strategies.base import DefaultStrategy
from FortyFour.accounting.strategies.syscohada import SyscohadaStrategy


class MockAccount:
    def __init__(self, code: str, account_class: int | None = None):
        self.code = code
        self.account_class = account_class
        self.name = ""
        self.description = ""
        self.account_type = ""
        self.normal_balance = ""


def test_default_strategy_classifies_asset() -> None:
    strategy = DefaultStrategy()

    account = MockAccount(code="201", account_class=2)

    assert strategy.classify_statement_role(account, Decimal("100.00")) == "asset"


def test_syscohada_dynamic_balance() -> None:
    strategy = SyscohadaStrategy()

    bank_account = MockAccount(code="521", account_class=5)

    assert strategy.classify_statement_role(bank_account, Decimal("100.00")) == "asset"
    assert strategy.classify_statement_role(bank_account, Decimal("-50.00")) == "liability"


def test_syscohada_class_8() -> None:
    strategy = SyscohadaStrategy()

    expense_account = MockAccount(code="81", account_class=8)
    revenue_account = MockAccount(code="82", account_class=8)

    assert strategy.classify_statement_role(expense_account, Decimal("0.00")) == "expense"
    assert strategy.classify_statement_role(revenue_account, Decimal("0.00")) == "revenue"


def test_syscohada_cash_flow_role_uses_ohada_families_without_account_type() -> None:
    strategy = SyscohadaStrategy()

    long_term_loan = MockAccount(code="161", account_class=1)
    equipment = MockAccount(code="245", account_class=2)
    supplier = MockAccount(code="401", account_class=4)

    assert strategy.classify_cash_flow_role(long_term_loan) == "financing"
    assert strategy.classify_cash_flow_role(equipment) == "investing"
    assert strategy.classify_cash_flow_role(supplier) == "operating"