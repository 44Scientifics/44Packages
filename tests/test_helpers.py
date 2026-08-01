import pytest
from FortyFour.Utils.helpers import (
    serialize_date_in_dict,
    remove_nan_values_from_dict,
    sort_dict_by_key,
    update_list_from_new_source_keep_old_matches,
)


class TestRemoveNanValues:
    def test_filters_nan(self):
        result = remove_nan_values_from_dict({"a": float("nan"), "b": 1})
        assert "a" not in result
        assert result["b"] == 1

    def test_preserves_non_nan(self):
        result = remove_nan_values_from_dict({"a": "hello", "b": 42, "c": 3.14})
        assert result == {"a": "hello", "b": 42, "c": 3.14}

    def test_handles_nested_dict(self):
        result = remove_nan_values_from_dict({"a": {"x": float("nan"), "y": "ok"}, "b": 1})
        assert result == {"a": {"y": "ok"}, "b": 1}

    def test_returns_new_dict(self):
        original = {"a": float("nan"), "b": 1}
        result = remove_nan_values_from_dict(original)
        assert result is not original
        assert "a" in original  # original unchanged


class TestSerializeDateInDict:
    def test_parses_iso_date(self):
        from datetime import datetime
        result = serialize_date_in_dict({"date": "2024-06-25"})
        assert isinstance(result["date"], datetime)
        assert result["date"].year == 2024
        assert result["date"].month == 6
        assert result["date"].day == 25

    def test_does_not_mutate_input(self):
        original = {"date": "2024-06-25"}
        result = serialize_date_in_dict(original)
        assert result is not original
        assert isinstance(original["date"], str)  # original unchanged

    def test_silent_mode(self):
        result = serialize_date_in_dict({"not_a_date": "xyz"}, silent=True)
        assert result["not_a_date"] == "xyz"  # kept as-is


class TestSortDictByKey:
    def test_sorts_correctly(self):
        items = [{"name": "C"}, {"name": "A"}, {"name": "B"}]
        result = sort_dict_by_key(items, "name", reverse=False)
        assert [d["name"] for d in result] == ["A", "B", "C"]

    def test_reverse_sort(self):
        items = [{"name": "A"}, {"name": "C"}, {"name": "B"}]
        result = sort_dict_by_key(items, "name", reverse=True)
        assert [d["name"] for d in result] == ["C", "B", "A"]


class TestUpdateListFromNewSource:
    def test_merges_old_and_new(self):
        old = [{"_id": "1", "ticker": "AAPL", "comment": "old note"}]
        new = [{"_id": "1", "ticker": "AAPL", "price": 150.0}, {"_id": "2", "ticker": "GOOG"}]
        result = update_list_from_new_source_keep_old_matches(old, new)
        assert len(result) == 2
        aapl = next(d for d in result if d["_id"] == "1")
        assert aapl["comment"] == "old note"  # preserved from old
        assert aapl["price"] == 150.0  # overridden by new
        goog = next(d for d in result if d["_id"] == "2")
        assert goog["avg_price"] == 0.0  # default applied

    def test_removes_deprecated(self):
        old = [{"_id": "1", "ticker": "AAPL"}, {"_id": "2", "ticker": "MSFT"}]
        new = [{"_id": "1", "ticker": "AAPL"}]
        result = update_list_from_new_source_keep_old_matches(old, new)
        assert len(result) == 1
        assert result[0]["_id"] == "1"
