"""
SQLAlchemy Fuzzy Search Utilities

Provides reusable functions for building PostgreSQL-powered fuzzy search
queries using the ``unaccent`` and ``pg_trgm`` extensions.

**Required PostgreSQL setup:** Run these once on your database:

    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE EXTENSION IF NOT EXISTS unaccent;
    CREATE OR REPLACE FUNCTION f_unaccent(text)
        RETURNS text AS $$
        SELECT public.unaccent('public.unaccent', $1)
    $$ LANGUAGE sql IMMUTABLE;

**Statement style:** ``apply_fuzzy_search`` operates on SQLAlchemy 2.0 Core
``Select`` statements (filtered via ``.where()``).
"""

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Select, String, Text, cast, func, or_
from sqlalchemy import inspect as sa_inspect
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
        # SAEnum subclasses String but is NOT searchable: on PostgreSQL there is
        # no implicit enum->text cast, so f_unaccent(coalesce(enum_col, ''))
        # fails at runtime. Explicitly exclude enum-typed columns.
        if isinstance(col.type, _SEARCHABLE_TYPES) and not isinstance(col.type, SAEnum):
            columns.append(col)
    return columns


def _resolve_columns(statement, items: tuple) -> list:
    """
    Resolve the *columns argument into a flat list of column elements.

    Handles three cases:
      - ColumnElement: kept as-is.
      - Model class (has __table__): extracts its String/Text columns.
      - Empty tuple: infers the model from the statement's column_descriptions.
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


def _coerce_searchable(column: ColumnElement) -> ColumnElement:
    """
    Return a column safely usable with f_unaccent/coalesce.

    Enum-typed columns are cast to String explicitly: PostgreSQL has no
    implicit enum->text cast, so coalesce(enum_col, '') alone fails at
    runtime. Non-enum columns pass through unchanged.
    """
    if isinstance(getattr(column, "type", None), SAEnum):
        return cast(column, String)
    return column


def fuzzy_match(column: ColumnElement, term: str) -> ColumnElement:
    """
    Build a single fuzzy match condition for one column.
    Uses the word_similarity operator (<%), which applies the session-global
    ``pg_trgm.word_similarity_threshold`` (default 0.3).
    """
    column = _coerce_searchable(column)
    return func.f_unaccent(term).bool_op("<%")(func.f_unaccent(func.coalesce(column, "")))


def fuzzy_similarity(column: ColumnElement, term: str) -> ColumnElement:
    """
    Compute the trigram word_similarity score between a search term and a column.
    """
    column = _coerce_searchable(column)
    return func.word_similarity(func.f_unaccent(term), func.f_unaccent(func.coalesce(column, "")))


def _match_condition(column: ColumnElement, term: str, threshold: float | None) -> ColumnElement:
    """
    Build the match predicate for one column.

    - ``threshold is None`` (default): ``<%`` operator — uses the session-global
      ``pg_trgm.word_similarity_threshold``, index-friendly.
    - ``threshold`` provided: explicit ``word_similarity(...) >= threshold``
      comparison (no index use, acceptable on small volumes).
    """
    if threshold is None:
        return fuzzy_match(column, term)
    return fuzzy_similarity(column, term) >= threshold


def apply_fuzzy_search(
    statement: Select,
    query_text: str,
    *columns: ColumnElement,
    threshold: float | None = None,
) -> Select:
    """
    Apply fuzzy, accent-insensitive search across one or more columns.

    - Filters rows where ANY of the given columns fuzzy-match the term
      (pg_trgm word_similarity against the session-global
      ``pg_trgm.word_similarity_threshold``, default 0.3).
    - ``threshold`` overrides the similarity threshold for this call via an
      explicit ``word_similarity(...) >= threshold`` comparison.
    - Orders results by the BEST similarity score (descending). Note: the
      ``order_by`` is appended — do not pre-order the statement when relying
      on relevance ordering.

    Accepts individual column attributes, full model classes, or nothing
    (in which case the model is inferred from the statement). Operates on
    SQLAlchemy 2.0 Core ``Select`` statements.

    Pure statement builder: returns a new statement — it never executes.
    """
    if not query_text:
        return statement

    resolved = _resolve_columns(statement, columns)
    if not resolved:
        return statement

    # Build OR filter: match on any column
    conditions = [_match_condition(col, query_text, threshold) for col in resolved]
    statement = statement.where(or_(*conditions))

    # Build relevance score: take the MAX similarity across all columns
    if len(resolved) == 1:
        relevance = fuzzy_similarity(resolved[0], query_text)
    else:
        relevance = func.greatest(*[fuzzy_similarity(col, query_text) for col in resolved])

    statement = statement.order_by(relevance.desc())

    return statement
