"""
SQLAlchemy Fuzzy Search Utilities

Provides reusable functions for building PostgreSQL-powered fuzzy search
queries using the `unaccent` and `pg_trgm` extensions.
"""

from sqlalchemy import func, or_, String, Text, inspect as sa_inspect
from sqlalchemy.orm import Query
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


def _resolve_columns(query: Query, items: tuple) -> list:
    """
    Resolve the *columns argument into a flat list of column elements.

    Handles three cases:
      - ColumnElement: kept as-is.
      - Model class (has __table__): extracts its String/Text columns.
      - Empty tuple: infers the model from the query's column_descriptions.
    """
    columns = []

    # If nothing was passed, infer the model from the query.
    if not items:
        try:
            for desc in query.column_descriptions:
                entity = desc.get("entity")
                if entity and hasattr(entity, "__table__"):
                    columns.extend(_extract_string_columns(entity))
        except Exception:
            pass
        return columns

    for item in items:
        if hasattr(item, "__table__"):
            # It's a model class — expand to its string columns.
            columns.extend(_extract_string_columns(item))
        else:
            columns.append(item)

    return columns


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


def apply_fuzzy_search(query: Query, term: str, *columns: ColumnElement) -> Query:
    """
    Apply fuzzy, accent-insensitive search across one or more columns.

    - Filters rows where ANY of the given columns fuzzy-match the term.
    - Orders results by the BEST similarity score (descending).

    Accepts individual column attributes, full model classes, or nothing
    (in which case the model is inferred from the query).
    """
    resolved = _resolve_columns(query, columns)
    if not resolved:
        return query

    # Build OR filter: match on any column
    conditions = [fuzzy_match(col, term) for col in resolved]
    query = query.filter(or_(*conditions))

    # Build relevance score: take the MAX similarity across all columns
    if len(resolved) == 1:
        relevance = fuzzy_similarity(resolved[0], term)
    else:
        relevance = func.greatest(*[fuzzy_similarity(col, term) for col in resolved])

    query = query.order_by(relevance.desc())

    return query
