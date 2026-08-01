import pytest
from unittest.mock import MagicMock
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from FortyFour.Utils.search import (
    fuzzy_match,
    fuzzy_similarity,
    apply_fuzzy_search,
    _extract_string_columns,
)


def test_fuzzy_match_builds_expression():
    col = MagicMock()
    expr = fuzzy_match(col, "test")
    assert expr is not None


def test_fuzzy_similarity_builds_expression():
    col = MagicMock()
    expr = fuzzy_similarity(col, "test")
    assert expr is not None


def test_apply_fuzzy_search_no_columns_noop():
    mock_query = MagicMock()
    result = apply_fuzzy_search(mock_query, "test")  # no columns
    assert result is mock_query  # returned unchanged


def test_extract_string_columns_skips_non_string():
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    cols = _extract_string_columns(TestModel)
    col_names = [c.name for c in cols]
    assert "name" in col_names
    assert "id" not in col_names
