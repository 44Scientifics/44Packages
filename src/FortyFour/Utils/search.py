"""
SQLAlchemy Fuzzy Search Utilities

Provides reusable functions for building PostgreSQL-powered fuzzy search
queries using the `unaccent` and `pg_trgm` extensions, with a
case-insensitive ``LIKE`` fallback for SQLite.

**Required PostgreSQL setup:** Run these once on your database:

    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE EXTENSION IF NOT EXISTS unaccent;
    CREATE OR REPLACE FUNCTION f_unaccent(text)
        RETURNS text AS $$
        SELECT public.unaccent('public.unaccent', $1)
    $$ LANGUAGE sql IMMUTABLE;

**Dual-style support:** ``apply_fuzzy_search`` accepts both SQLAlchemy 1.x
ORM ``Query`` objects (filtered via ``.filter()``) and 2.0 Core ``Select``
statements (filtered via ``.where()``). The correct method is chosen by
duck-typing: ``.filter()`` is tried first, falling back to ``.where()``.

**Dialect:** pass ``dialect="sqlite"`` when building queries against a
SQLite database — pg_trgm/unaccent operators are unavailable there, so a
case-insensitive ``LIKE`` predicate is used instead. The dialect is an
explicit parameter; this module never reads application configuration.
"""

from sqlalchemy import Select, String, Text, cast, func, or_
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.sql.elements import ColumnElement

# Column types considered "searchable" — only String/Text families.
_SEARCHABLE_TYPES = (String, Text)


def _extract_string_columns(model) -> list:
    """
    Extract all String/Text column attributes from a SQLAlchemy model class.

    Skips non-string columns (UUID, Integer, Numeric, Boolean, DateTime, etc.)
    to keep trigram searches efficient and type-safe.
    """
    mapper = sa_inspect(model).mapper
    columns = []
    for attr in mapper.column_attrs:
        col = attr.columns[0]
        if isinstance(col.type, _SEARCHABLE_TYPES):
            columns.append(col)
    return columns


def _resolve_columns(statement, items: tuple) -> list:
    """
    Resolve the *columns argument into a flat list of column elements.

    Handles three cases:
      - ColumnElement: kept as-is.
      - Model class (has __table__): extracts its String/Text columns.
      - Empty tuple: infers the model from the statement's column_descriptions.

    Works for both ORM ``Query`` and Core ``Select`` statements.
    """
    columns = []

    # If nothing was passed, infer the model from the statement.
    if not items:
        try:
            for desc in statement.column_descriptions:
                entity = desc.get("entity")
                if entity and hasattr(entity, "__table__"):
                    columns.extend(_extract_string_columns(entity))
        except (AttributeError, TypeError, UnmappedClassError):
            # Best-effort inference: fall back to an empty column list.
            pass
        return columns

    for item in items:
        if hasattr(item, "__table__"):
            # It's a model class — expand to its string columns.
            columns.extend(_extract_string_columns(item))
        else:
            columns.append(item)

    return columns


def _apply_criteria(statement, criteria) -> Query | Select:
    """
    Apply a filter criteria to either an ORM ``Query`` or a Core ``Select``.

    Duck-typing: try ``.filter()`` first (ORM Query), fall back to
    ``.where()`` (Core Select, or any where()-only statement object).
    """
    try:
        return statement.filter(criteria)
    except AttributeError:
        return statement.where(criteria)


def fuzzy_match(column: ColumnElement, term: str) -> ColumnElement:
    """
    Build a single fuzzy match condition for one column.
    Uses word_similarity operator (<%).
    """
    return func.f_unaccent(term).bool_op("<%")(func.f_unaccent(func.coalesce(column, "")))


def fuzzy_similarity(column: ColumnElement, term: str) -> ColumnElement:
    """
    Compute the trigram word_similarity score between a search term and a column.
    """
    return func.word_similarity(func.f_unaccent(term), func.f_unaccent(func.coalesce(column, "")))


def apply_fuzzy_search(
    statement: Query | Select,
    query_text: str,
    *columns: ColumnElement,
    dialect: str = "postgresql",
) -> Query | Select:
    """
    Apply fuzzy, accent-insensitive search across one or more columns.

    - Filters rows where ANY of the given columns fuzzy-match the term.
    - Orders results by the BEST similarity score (descending) on PostgreSQL.

    Accepts individual column attributes, full model classes, or nothing
    (in which case the model is inferred from the statement). Both ORM
    ``Query`` objects (``.filter()``) and 2.0 Core ``Select`` statements
    (``.where()``) are supported via duck-typing.

    ``dialect`` selects the backend strategy:
      - ``"postgresql"`` (default): pg_trgm/unaccent operators.
      - ``"sqlite"``: case-insensitive ``LIKE`` on lowercase text.

    Pure statement builder: returns a new statement — it never executes.
    """
    if not query_text:
        return statement

    resolved = _resolve_columns(statement, columns)
    if not resolved:
        return statement

    if dialect == "sqlite":
        # SQLite fallback: pg_trgm/unaccent operators are unavailable — use a
        # case-insensitive LIKE on the raw text columns instead.
        normalized_query = f"%{query_text.lower()}%"
        predicates = [
            func.lower(func.coalesce(cast(col, String), "")).like(normalized_query)
            for col in resolved
        ]
        return _apply_criteria(statement, or_(*predicates))

    # Build OR filter: match on any column
    conditions = [fuzzy_match(col, query_text) for col in resolved]
    statement = _apply_criteria(statement, or_(*conditions))

    # Build relevance score: take the MAX similarity across all columns
    if len(resolved) == 1:
        relevance = fuzzy_similarity(resolved[0], query_text)
    else:
        relevance = func.greatest(*[fuzzy_similarity(col, query_text) for col in resolved])

    statement = statement.order_by(relevance.desc())

    return statement
