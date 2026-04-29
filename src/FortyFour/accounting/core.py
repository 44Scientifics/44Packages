from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Sequence
from uuid import UUID


ZERO = Decimal("0.00")
DEFAULT_ACCOUNT_CLASS_BY_TYPE = {
    "asset": 5,
    "liability": 4,
    "equity": 1,
    "expense": 6,
    "revenue": 7,
    "income": 7,
}
TREASURY_ACCOUNT_NAME_MARKERS = (
    "bank",
    "cash",
    "treasury",
    "checking",
    "savings",
    "wallet",
    "petty cash",
    "banque",
    "caisse",
    "tresorerie",
    "trésorerie",
)
INVESTING_ACCOUNT_NAME_MARKERS = (
    "equipment",
    "vehicle",
    "machinery",
    "property",
    "plant",
    "software",
    "license",
    "licence",
    "fixed asset",
    "immobil",
    "capex",
)
FINANCING_ACCOUNT_NAME_MARKERS = (
    "loan",
    "debt",
    "borrow",
    "lease",
    "financing",
    "emprunt",
    "dette",
    "pret",
    "prêt",
)
NON_OPERATING_RESULT_NAME_MARKERS = (
    "gain",
    "loss",
    "disposal",
    "asset sale",
    "sale of asset",
    "cession",
    "plus-value",
    "plus value",
    "moins-value",
    "minus-value",
    "revaluation",
    "write-off",
    "write off",
)
TREASURY_ACCOUNT_CODE_PREFIXES = (
    "51",
    "53",
    "54",
    "58",
)


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    id: UUID
    code: str
    name: str
    account_type: str
    account_class: int | None = None
    normal_balance: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class EntryLineSnapshot:
    account_id: UUID
    account: AccountSnapshot
    debit: Decimal = ZERO
    credit: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class JournalEntrySnapshot:
    lines: tuple[EntryLineSnapshot, ...]


def to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


def get_line_value(line: Any, field_name: str, default: Any = ZERO) -> Any:
    if isinstance(line, dict):
        return line.get(field_name, default)
    return getattr(line, field_name, default)


def normalize_account_ids(account_ids: Iterable[UUID] | None) -> set[UUID]:
    return set(account_ids or [])


def account_text(account: Any | None) -> str:
    if not account:
        return ""
    return " ".join(
        str(value).strip()
        for value in (
            get_line_value(account, "code", ""),
            get_line_value(account, "name", ""),
            get_line_value(account, "description", ""),
        )
        if value
    ).casefold()


def account_code(account: Any | None) -> str:
    if not account:
        return ""
    return str(get_line_value(account, "code", "") or "").strip()


def resolved_pcg_class(account: Any | None) -> int | None:
    if not account:
        return None

    code = account_code(account)
    code_class = None
    if code and code[0].isdigit():
        code_class = int(code[0])

    raw_account_class = get_line_value(account, "account_class", None)
    stored_class = None
    try:
        if raw_account_class is not None:
            stored_class = int(raw_account_class)
    except (TypeError, ValueError):
        stored_class = None

    account_type = str(get_line_value(account, "account_type", "") or "").strip().lower()
    default_class = DEFAULT_ACCOUNT_CLASS_BY_TYPE.get(account_type)
    if stored_class is not None and stored_class != default_class:
        return stored_class
    if code_class is not None:
        return code_class
    return stored_class


def account_code_matches_prefixes(account: Any | None, prefixes: Sequence[str]) -> bool:
    code = account_code(account)
    return any(code.startswith(prefix) for prefix in prefixes)


def is_treasury_account(
    account: Any | None,
    treasury_account_ids: Iterable[UUID] | None = None,
) -> bool:
    if not account:
        return False

    treasury_account_id_set = normalize_account_ids(treasury_account_ids)
    if treasury_account_id_set:
        return get_line_value(account, "id", None) in treasury_account_id_set
    if get_line_value(account, "account_type", None) != "asset":
        return False
    if resolved_pcg_class(account) == 5 and account_code_matches_prefixes(account, TREASURY_ACCOUNT_CODE_PREFIXES):
        return True

    return any(marker in account_text(account) for marker in TREASURY_ACCOUNT_NAME_MARKERS)


def classify_cash_flow_account(
    account: Any,
    investing_account_ids: Iterable[UUID] | None = None,
    financing_account_ids: Iterable[UUID] | None = None,
) -> str:
    account_id = get_line_value(account, "id", None)
    investing_account_id_set = normalize_account_ids(investing_account_ids)
    financing_account_id_set = normalize_account_ids(financing_account_ids)

    if financing_account_id_set and account_id in financing_account_id_set:
        return "financing"
    if investing_account_id_set and account_id in investing_account_id_set:
        return "investing"

    pcg_class = resolved_pcg_class(account)
    normalized_account_type = str(get_line_value(account, "account_type", "") or "").strip().lower()
    normalized_account_text = account_text(account)
    if normalized_account_type == "equity":
        return "financing"
    if normalized_account_type == "liability" and pcg_class == 1:
        return "financing"
    if normalized_account_type == "asset" and pcg_class == 2:
        return "investing"
    if normalized_account_type == "liability":
        if any(marker in normalized_account_text for marker in FINANCING_ACCOUNT_NAME_MARKERS):
            return "financing"
        return "operating"
    if any(marker in normalized_account_text for marker in INVESTING_ACCOUNT_NAME_MARKERS):
        return "investing"
    return "operating"


def is_supporting_non_operating_result_account(account: Any) -> bool:
    normalized_account_type = str(get_line_value(account, "account_type", "") or "").strip().lower()
    if normalized_account_type not in {"expense", "revenue", "income"}:
        return False
    return any(marker in account_text(account) for marker in NON_OPERATING_RESULT_NAME_MARKERS)


def allocate_cash_flow_amount(
    treasury_change: Decimal,
    counterpart_lines: list[Any],
    side_field: str,
) -> list[tuple[Any, Decimal]]:
    total_basis = sum((to_decimal(get_line_value(line, side_field)) for line in counterpart_lines), ZERO)
    if total_basis == ZERO:
        return []

    remaining = abs(treasury_change)
    allocations: list[tuple[Any, Decimal]] = []
    sign = Decimal("1.00") if treasury_change >= ZERO else Decimal("-1.00")

    for index, line in enumerate(counterpart_lines):
        if index == len(counterpart_lines) - 1:
            allocated = remaining
        else:
            basis = to_decimal(get_line_value(line, side_field))
            allocated = to_decimal(abs(treasury_change) * basis / total_basis)
            remaining -= allocated
        allocations.append((line, allocated * sign))

    return allocations


def select_counterpart_lines_for_cash_flow(
    counterpart_lines: list[Any],
    investing_account_ids: Iterable[UUID] | None = None,
    financing_account_ids: Iterable[UUID] | None = None,
) -> list[Any]:
    classified_lines = [
        (
            line,
            classify_cash_flow_account(
                get_line_value(line, "account", None),
                investing_account_ids,
                financing_account_ids,
            ),
        )
        for line in counterpart_lines
    ]
    non_operating_sections = {
        section
        for _, section in classified_lines
        if section in {"investing", "financing"}
    }

    if len(non_operating_sections) == 1:
        target_section = next(iter(non_operating_sections))
        operating_lines = [line for line, section in classified_lines if section == "operating"]
        if operating_lines and not all(
            is_supporting_non_operating_result_account(get_line_value(line, "account", None))
            for line in operating_lines
        ):
            return counterpart_lines
        return [line for line, section in classified_lines if section == target_section]

    return counterpart_lines


def accumulate_cash_flow_line(bucket: dict[UUID, dict[str, Any]], line: Any, amount: Decimal) -> None:
    account_id = get_line_value(line, "account_id", None)
    account = get_line_value(line, "account", None)
    existing = bucket.get(account_id)
    if existing is None:
        existing = {
            "account_id": account_id,
            "account_code": get_line_value(account, "code", ""),
            "account_name": get_line_value(account, "name", ""),
            "amount": ZERO,
        }
        bucket[account_id] = existing
    existing["amount"] += amount


def validate_journal_entry_lines(lines: Sequence[Any]) -> None:
    if len(lines) < 2:
        raise ValueError("A journal entry must contain at least two lines")

    total_debit = ZERO
    total_credit = ZERO

    for line in lines:
        debit = to_decimal(get_line_value(line, "debit"))
        credit = to_decimal(get_line_value(line, "credit"))

        if debit < 0 or credit < 0:
            raise ValueError("Journal entry lines cannot contain negative amounts")
        if (debit > 0) == (credit > 0):
            raise ValueError("Each journal line must have exactly one positive side: debit or credit")

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise ValueError("Journal entry lines must be balanced")


def statement_section(title: str, items: list[dict], amount_field: str = "net_balance") -> dict[str, Any]:
    lines = [
        {
            "account_id": item["account_id"],
            "account_code": item["account_code"],
            "account_name": item["account_name"],
            "amount": to_decimal(item[amount_field]),
        }
        for item in items
        if to_decimal(item[amount_field]) != ZERO
    ]
    lines.sort(key=lambda item: (item["account_code"], item["account_name"]))
    total = sum((line["amount"] for line in lines), ZERO)
    return {"title": title, "total": total, "lines": lines}


def build_trial_balance(
    company_id: UUID,
    items: list[dict[str, Any]],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    total_debit = sum((to_decimal(item["debit"]) for item in items), ZERO)
    total_credit = sum((to_decimal(item["credit"]) for item in items), ZERO)
    return {
        "company_id": company_id,
        "start_date": start_date,
        "end_date": end_date,
        "items": items,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "generated_at": generated_at or datetime.now(timezone.utc),
    }


def build_income_statement(
    company_id: UUID,
    revenue_items: list[dict[str, Any]],
    expense_items: list[dict[str, Any]],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    revenues = statement_section("Revenues", revenue_items)
    expenses = statement_section("Expenses", expense_items)
    total_revenue = revenues["total"]
    total_expenses = expenses["total"]
    return {
        "company_id": company_id,
        "start_date": start_date,
        "end_date": end_date,
        "revenues": revenues,
        "expenses": expenses,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_income": total_revenue - total_expenses,
        "generated_at": generated_at or datetime.now(timezone.utc),
    }


def build_balance_sheet(
    company_id: UUID,
    end_date: datetime,
    asset_items: list[dict[str, Any]],
    liability_items: list[dict[str, Any]],
    equity_items: list[dict[str, Any]],
    net_income: Decimal = ZERO,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    equity_section = statement_section("Equity", equity_items)
    if net_income != ZERO:
        equity_section["lines"].append(
            {
                "account_id": UUID("00000000-0000-0000-0000-000000000000"),
                "account_code": "RESULT",
                "account_name": "Current period result",
                "amount": to_decimal(net_income),
            }
        )
        equity_section["total"] += to_decimal(net_income)

    assets = statement_section("Assets", asset_items)
    liabilities = statement_section("Liabilities", liability_items)
    total_assets = assets["total"]
    total_liabilities_and_equity = liabilities["total"] + equity_section["total"]

    return {
        "company_id": company_id,
        "end_date": end_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity_section,
        "total_assets": total_assets,
        "total_liabilities_and_equity": total_liabilities_and_equity,
        "generated_at": generated_at or datetime.now(timezone.utc),
    }


def build_cash_flow_statement(
    company_id: UUID,
    entries: Sequence[Any],
    closing_cash_balance: Decimal,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    treasury_account_ids: Iterable[UUID] | None = None,
    investing_account_ids: Iterable[UUID] | None = None,
    financing_account_ids: Iterable[UUID] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    treasury_account_id_set = normalize_account_ids(treasury_account_ids)
    investing_account_id_set = normalize_account_ids(investing_account_ids)
    financing_account_id_set = normalize_account_ids(financing_account_ids)
    section_buckets: dict[str, dict[UUID, dict[str, Any]]] = {
        "operating": {},
        "investing": {},
        "financing": {},
    }
    net_change_in_cash = ZERO

    for entry in entries:
        entry_lines = list(get_line_value(entry, "lines", []))
        treasury_lines = [
            line
            for line in entry_lines
            if is_treasury_account(get_line_value(line, "account", None), treasury_account_id_set)
        ]
        if not treasury_lines:
            continue

        treasury_change = sum(
            (
                to_decimal(get_line_value(line, "debit")) - to_decimal(get_line_value(line, "credit"))
                for line in treasury_lines
            ),
            ZERO,
        )
        if treasury_change == ZERO:
            continue

        side_field = "credit" if treasury_change > ZERO else "debit"
        counterpart_lines = [
            line
            for line in entry_lines
            if not is_treasury_account(get_line_value(line, "account", None), treasury_account_id_set)
            and to_decimal(get_line_value(line, side_field)) > ZERO
        ]
        if not counterpart_lines:
            continue

        counterpart_lines = select_counterpart_lines_for_cash_flow(
            counterpart_lines,
            investing_account_id_set,
            financing_account_id_set,
        )

        net_change_in_cash += treasury_change
        for counterpart_line, amount in allocate_cash_flow_amount(treasury_change, counterpart_lines, side_field):
            section_key = classify_cash_flow_account(
                get_line_value(counterpart_line, "account", None),
                investing_account_id_set,
                financing_account_id_set,
            )
            accumulate_cash_flow_line(section_buckets[section_key], counterpart_line, amount)

    normalized_closing_cash_balance = to_decimal(closing_cash_balance)
    operating_activities = statement_section(
        "Operating activities",
        list(section_buckets["operating"].values()),
        amount_field="amount",
    )
    investing_activities = statement_section(
        "Investing activities",
        list(section_buckets["investing"].values()),
        amount_field="amount",
    )
    financing_activities = statement_section(
        "Financing activities",
        list(section_buckets["financing"].values()),
        amount_field="amount",
    )

    return {
        "company_id": company_id,
        "start_date": start_date,
        "end_date": end_date,
        "operating_activities": operating_activities,
        "investing_activities": investing_activities,
        "financing_activities": financing_activities,
        "net_change_in_cash": to_decimal(net_change_in_cash),
        "opening_cash_balance": to_decimal(normalized_closing_cash_balance - net_change_in_cash),
        "closing_cash_balance": normalized_closing_cash_balance,
        "generated_at": generated_at or datetime.now(timezone.utc),
    }


__all__ = [
    "AccountSnapshot",
    "EntryLineSnapshot",
    "JournalEntrySnapshot",
    "ZERO",
    "account_code",
    "account_code_matches_prefixes",
    "account_text",
    "accumulate_cash_flow_line",
    "allocate_cash_flow_amount",
    "build_balance_sheet",
    "build_cash_flow_statement",
    "build_income_statement",
    "build_trial_balance",
    "classify_cash_flow_account",
    "get_line_value",
    "is_supporting_non_operating_result_account",
    "is_treasury_account",
    "normalize_account_ids",
    "resolved_pcg_class",
    "select_counterpart_lines_for_cash_flow",
    "statement_section",
    "to_decimal",
    "validate_journal_entry_lines",
]