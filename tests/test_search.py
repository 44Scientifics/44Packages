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
    assert apply_fuzzy_search(stmt, "", TestModel.name, dialect="sqlite") is stmt
    assert apply_fuzzy_search(stmt, None, TestModel.name) is stmt


def test_apply_fuzzy_search_sqlite_uses_case_insensitive_like():
    """SQLite dialect builds a case-insensitive LIKE predicate (no pg_trgm)."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_sqlite_like"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    stmt = select(TestModel)
    result = apply_fuzzy_search(stmt, "alpha", TestModel.name, dialect="sqlite")

    compiled = str(result.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "lower(" in compiled
    assert "like" in compiled
    assert "%alpha%" in compiled


def test_apply_fuzzy_search_sqlite_roundtrip():
    """SQLite LIKE fallback filters rows end-to-end on an in-memory database."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_sqlite_roundtrip"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                TestModel(name="Alpha Beta"),
                TestModel(name="Gamma Delta"),
            ]
        )
        session.commit()

        stmt = select(TestModel)
        result = apply_fuzzy_search(stmt, "alpha", TestModel.name, dialect="sqlite")
        rows = session.execute(result).scalars().all()
        assert [row.name for row in rows] == ["Alpha Beta"]


def test_apply_fuzzy_search_sqlite_multiple_columns_ored():
    """Multiple columns produce OR'ed LIKE predicates on SQLite."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_sqlite_or"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        description = Column(String)

    stmt = select(TestModel)
    result = apply_fuzzy_search(
        stmt, "alpha", TestModel.name, TestModel.description, dialect="sqlite"
    )

    compiled = str(result.compile())
    assert "OR" in compiled.upper()
    assert compiled.lower().count("like") == 2


def test_apply_fuzzy_search_orm_query_dual_style():
    """ORM Query objects are supported via the .filter() path (default dialect)."""
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_orm_query"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    query = Query(TestModel)
    result = apply_fuzzy_search(query, "hello", TestModel.name)
    assert isinstance(result, Query)
    assert result.whereclause is not None


def test_apply_fuzzy_search_select_dual_style():
    """Core Select statements are supported via the .where() path."""
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
