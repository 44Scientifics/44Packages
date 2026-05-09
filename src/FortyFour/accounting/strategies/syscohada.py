from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..core import account_code, account_code_matches_prefixes, resolve_pcg_class_with_source
from .base import DefaultStrategy


SYSCOHADA_FINANCING_CODE_PREFIXES = (
    "10",
    "11",
    "12",
    "13",
    "14",
    "16",
    "17",
    "18",
)
SYSCOHADA_INVESTING_CODE_PREFIXES = (
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
)
SYSCOHADA_OPERATING_CODE_PREFIXES = (
    "40",
    "41",
    "42",
    "43",
    "44",
    "45",
    "46",
    "47",
    "48",
)
SYSCOHADA_TREASURY_CODE_PREFIXES = (
    "51",
    "52",
    "53",
    "54",
    "56",
    "57",
    "58",
)


class SyscohadaStrategy(DefaultStrategy):
    def classify_statement_role(self, account: Any, net_balance: Decimal) -> str:
        pcg_class, _ = resolve_pcg_class_with_source(account)
        code = account_code(account)

        if pcg_class == 8 and len(code) >= 2:
            try:
                sub_class = int(code[:2])
            except ValueError:
                sub_class = None
            if sub_class is not None:
                return "revenue" if sub_class % 2 == 0 else "expense"

        if pcg_class in {4, 5}:
            return "liability" if net_balance < Decimal("0.00") else "asset"

        return super().classify_statement_role(account, net_balance)

    def classify_cash_flow_role(self, account: Any) -> str:
        if self.is_treasury_account(account):
            return "treasury"
        if account_code_matches_prefixes(account, SYSCOHADA_FINANCING_CODE_PREFIXES):
            return "financing"
        if account_code_matches_prefixes(account, SYSCOHADA_INVESTING_CODE_PREFIXES):
            return "investing"
        if account_code_matches_prefixes(account, SYSCOHADA_OPERATING_CODE_PREFIXES):
            return "operating"
        return super().classify_cash_flow_role(account)

    def is_treasury_account(self, account: Any) -> bool:
        return account_code_matches_prefixes(account, SYSCOHADA_TREASURY_CODE_PREFIXES)