import enum
from unittest.mock import MagicMock

from sqlalchemy import Column, Enum, Integer, String, create_engine, select
from sqlalchemy.orm import Query, Session, declarative_base

from FortyFour.Utils.search import (
    _extract_string_columns,
    apply_fuzzy_search,
    fuzzy_match,
    fuzzy_similarity,
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


def test_extract_string_columns_skips_enum():
    """SAEnum subclasses String but must NOT be picked up by inference."""
    class Status(str, enum.Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"

    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_enum_skip"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        status = Column(Enum(Status))

    # Direct helper check.
    col_names = [c.name for c in _extract_string_columns(TestModel)]
    assert "name" in col_names
    assert "status" not in col_names

    # Inference through apply_fuzzy_search (no explicit columns) must also
    # exclude the enum column from the generated predicate (the SELECT list
    # legitimately still contains it — the whole entity is selected).
    stmt = select(TestModel)
    compiled = str(apply_fuzzy_search(stmt, "ac").compile())
    assert "coalesce(test_enum_skip.name" in compiled
    assert "coalesce(test_enum_skip.status" not in compiled


def test_apply_fuzzy_search_empty_term_returns_unchanged():
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_empty_term"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    stmt = select(TestModel)
    assert apply_fuzzy_search(stmt, "", TestModel.name) is stmt
    assert apply_fuzzy_search(stmt, None, TestModel.name) is stmt


def test_apply_fuzzy_search_select():
    """Core Select statements are filtered via .where() with pg_trgm operators."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_core_select"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    stmt = select(TestModel)
    result = apply_fuzzy_search(stmt, "hello", TestModel.name)
    assert isinstance(result, select(TestModel).__class__)
    compiled = str(result.compile())
    assert "<%" in compiled  # pg_trgm word_similarity operator
    assert "order by" in compiled.lower()  # relevance sort applied


def test_apply_fuzzy_search_multiple_columns_ored():
    """Multiple columns produce OR'ed fuzzy predicates."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_or"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        description = Column(String)

    stmt = select(TestModel)
    result = apply_fuzzy_search(stmt, "alpha", TestModel.name, TestModel.description)

    compiled = str(result.compile())
    assert compiled.upper().count("OR") >= 1
    assert compiled.count("<%") == 2


def test_apply_fuzzy_search_threshold_uses_explicit_comparison():
    """A provided threshold replaces the <% operator with word_similarity >= x."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_threshold"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    stmt = select(TestModel)
    result = apply_fuzzy_search(stmt, "hello", TestModel.name, threshold=0.5)

    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "<%" not in compiled
    assert "word_similarity" in compiled
    assert ">= 0.5" in compiled
