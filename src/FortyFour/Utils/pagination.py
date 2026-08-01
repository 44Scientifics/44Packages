"""
Reusable pagination and search dependency.

Provides a single ``Depends()``-compatible callable that each list endpoint
can inject via the ``Annotated`` pattern, eliminating duplicated parameter
definitions across routers.

**Optional dependency:** FastAPI is only required when this module is
actually used. The rest of the ``FortyFour`` library imports cleanly
without it.
"""
from dataclasses import dataclass
from typing import Annotated, Optional

try:
    from fastapi import Depends, Query
except ImportError as exc:  # pragma: no cover - depends on the runtime environment
    raise ImportError(
        "FortyFour.Utils.pagination requires FastAPI. "
        "Install it with `pip install fastapi`."
    ) from exc


@dataclass
class PaginationParams:
    """Standard pagination, search, and sort parameters for list endpoints."""
    page: int
    size: int
    q: Optional[str]  # noqa: UP045 - kept byte-for-byte identical to investos
    sort_by: str
    order: str


async def pagination(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=0, description="Items per page (0 for unlimited)"),
    q: Optional[str] = Query(None, description="Fuzzy search query for typo-tolerant matching across text fields"),  # noqa: UP045 - kept byte-for-byte identical to investos
    sort_by: str = Query("id", description="Field to sort by"),
    order: str = Query("asc", description="Sort direction (asc or desc)"),
) -> PaginationParams:
    """Return standardised pagination, search, and sort parameters."""
    return PaginationParams(page=page, size=size, q=q, sort_by=sort_by, order=order)


# Reusable alias for the PATCH-pattern `Annotated[..., Depends()]`
PaginationDep = Annotated[PaginationParams, Depends(pagination)]
