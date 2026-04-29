"""
Fuzzy & Accent-Tolerant Search Utilities

Provides reusable functions for building PostgreSQL-powered fuzzy search
queries using the `unaccent` and `pg_trgm` extensions.

Usage in routers:
    from app.utils.search import apply_fuzzy_search

    if q:
        query = apply_fuzzy_search(
            query, q,
            models.Contact.name,
            models.Contact.email,
            models.Contact.position,
        )
"""

from sqlalchemy import func, or_, literal
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement


def fuzzy_match(column: ColumnElement, term: str) -> ColumnElement:
    """
    Build a single fuzzy match condition for one column.
    Uses our custom IMMUTABLE f_unaccent() on both the column and the search term,
    then applies the pg_trgm word_similarity operator (<%).
    This is better for partial matches (finding a word within a longer string).

    Returns a boolean SQL expression: f_unaccent(term) <% f_unaccent(column)
    """
    return func.f_unaccent(term).bool_op("<%")(func.f_unaccent(func.coalesce(column, "")))


def fuzzy_similarity(column: ColumnElement, term: str) -> ColumnElement:
    """
    Compute the trigram word_similarity score between a search term and a column.
    Both sides are normalized with our custom IMMUTABLE f_unaccent().
    Returns a float between 0 and 1 (1 = identical).
    """
    return func.word_similarity(func.f_unaccent(term), func.f_unaccent(func.coalesce(column, "")))


def apply_fuzzy_search(query: Query, term: str, *columns: ColumnElement) -> Query:
    """
    Apply fuzzy, accent-insensitive search across one or more columns.

    - Filters rows where ANY of the given columns fuzzy-match the term.
    - Orders results by the BEST similarity score (descending) so the
      most relevant matches appear first.

    Args:
        query: The existing SQLAlchemy query to augment.
        term: The raw search string from the user (e.g., "Kone").
        *columns: One or more SQLAlchemy column attributes to search
                  (e.g., models.Contact.name, models.Contact.email).

    Returns:
        The filtered and ordered query.
    """
    if not columns:
        return query

    # Build OR filter: match on any column
    conditions = [fuzzy_match(col, term) for col in columns]
    query = query.filter(or_(*conditions))

    # Build relevance score: take the MAX similarity across all columns
    if len(columns) == 1:
        relevance = fuzzy_similarity(columns[0], term)
    else:
        relevance = func.greatest(*[fuzzy_similarity(col, term) for col in columns])

    query = query.order_by(relevance.desc())

    return query
