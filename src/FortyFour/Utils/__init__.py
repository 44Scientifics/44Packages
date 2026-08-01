from .aws import read_file_from_s3, upload_to_s3
from .cli_generator import OpenAPICLIGenerator
from .helpers import remove_nan_values_from_dict, serialize_date_in_dict
from .search import apply_fuzzy_search, fuzzy_match, fuzzy_similarity

__all__ = [
    "OpenAPICLIGenerator",
    "PaginationDep",
    "PaginationParams",
    "apply_fuzzy_search",
    "fuzzy_match",
    "fuzzy_similarity",
    "pagination",
    "read_file_from_s3",
    "remove_nan_values_from_dict",
    "serialize_date_in_dict",
    "upload_to_s3",
]


def __getattr__(name: str):
    """
    Lazily resolve pagination helpers so FastAPI stays an optional dependency.

    Importing ``FortyFour.Utils`` never requires FastAPI; the pagination
    symbols are only fetched (and FastAPI imported) when actually used.

    Uses ``importlib.import_module`` rather than ``from . import pagination``:
    the latter re-enters this ``__getattr__`` through the import machinery's
    ``hasattr`` check and recurses. The import system also attaches the
    submodule to this package as ``FortyFour.Utils.pagination`` — it is
    overwritten so the ``pagination`` *function* stays the package-level
    export, matching investos' API surface.
    """
    if name in {"PaginationParams", "pagination", "PaginationDep"}:
        import importlib

        _pagination_module = importlib.import_module(".pagination", __name__)
        globals()["pagination"] = _pagination_module.pagination
        return getattr(_pagination_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
