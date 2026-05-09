from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from ..core import (
    classify_cash_flow_account,
    infer_statement_role_from_pcg_class,
    resolve_pcg_class_with_source,
)


@runtime_checkable
class AccountingStrategy(Protocol):
    def classify_statement_role(self, account: Any, net_balance: Decimal) -> str:
        ...

    def classify_cash_flow_role(self, account: Any) -> str:
        ...

    def is_treasury_account(self, account: Any) -> bool:
        ...


class DefaultStrategy:
    def classify_statement_role(self, account: Any, net_balance: Decimal) -> str:
        pcg_class, _ = resolve_pcg_class_with_source(account)
        return infer_statement_role_from_pcg_class(pcg_class, account=account)

    def classify_cash_flow_role(self, account: Any) -> str:
        return classify_cash_flow_account(account)

    def is_treasury_account(self, account: Any) -> bool:
        return False