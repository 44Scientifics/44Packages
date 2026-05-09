"""Model registry for FortyFour.

Consumer applications (e.g. CompanyOS API Server) must call ``configure()``
at startup to inject their own SQLAlchemy model classes **before** any
accounting engine function is invoked.  This avoids duplicating model
definitions across projects while keeping the library self-contained.

Usage example::

    import FortyFour.models as ff_models
    from app.models import (
        ChartOfAccount, JournalEntry, JournalEntryLine, JournalEntryAttachment,
    )

    ff_models.configure(
        chart_of_account=ChartOfAccount,
        journal_entry=JournalEntry,
        journal_entry_line=JournalEntryLine,
        journal_entry_attachment=JournalEntryAttachment,
    )
"""

from __future__ import annotations

from typing import Any

# Sentinel attributes – replaced at runtime by ``configure()``.
ChartOfAccount: Any = None
JournalEntry: Any = None
JournalEntryLine: Any = None
JournalEntryAttachment: Any = None
JournalEntryStatus: Any = None

_configured = False


def _is_equivalent_model_registration(current: Any, new: Any) -> bool:
    if current is new:
        return True
    if current is None or new is None:
        return current is None and new is None

    return (
        getattr(current, "__module__", None) == getattr(new, "__module__", None)
        and getattr(current, "__qualname__", getattr(current, "__name__", None))
        == getattr(new, "__qualname__", getattr(new, "__name__", None))
    )


def configure(
    *,
    chart_of_account: Any,
    journal_entry: Any,
    journal_entry_line: Any,
    journal_entry_attachment: Any,
    journal_entry_status: Any = None,
) -> None:
    """Register the SQLAlchemy model classes used by the accounting engine.

    Must be called before any ``FortyFour.accounting`` engine function is
    used. Repeated calls are accepted only when they re-register the same
    application model set after a module reload.
    """
    global ChartOfAccount, JournalEntry, JournalEntryLine, JournalEntryAttachment, JournalEntryStatus, _configured

    if _configured:
        if (
            _is_equivalent_model_registration(ChartOfAccount, chart_of_account)
            and _is_equivalent_model_registration(JournalEntry, journal_entry)
            and _is_equivalent_model_registration(JournalEntryLine, journal_entry_line)
            and _is_equivalent_model_registration(JournalEntryAttachment, journal_entry_attachment)
            and _is_equivalent_model_registration(JournalEntryStatus, journal_entry_status)
        ):
            ChartOfAccount = chart_of_account
            JournalEntry = journal_entry
            JournalEntryLine = journal_entry_line
            JournalEntryAttachment = journal_entry_attachment
            JournalEntryStatus = journal_entry_status
            return

        raise RuntimeError(
            "FortyFour.models.configure() has already been called. "
            "Model registration must happen exactly once at application startup."
        )

    ChartOfAccount = chart_of_account
    JournalEntry = journal_entry
    JournalEntryLine = journal_entry_line
    JournalEntryAttachment = journal_entry_attachment
    JournalEntryStatus = journal_entry_status
    _configured = True


def _assert_configured() -> None:
    """Guard called internally to fail fast with a clear message."""
    if not _configured:
        raise RuntimeError(
            "FortyFour.models has not been configured. "
            "Call FortyFour.models.configure(...) at application startup before "
            "using accounting engine functions."
        )
