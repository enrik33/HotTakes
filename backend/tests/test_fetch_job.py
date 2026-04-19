"""
Tests for the periodic HN fetch job (app/tasks/fetch_job.py).

Covers:
  - Successful run logs completion and clears the running flag.
  - Overlap prevention: second call while first is in progress is skipped.
  - Exceptions in ingestion are caught and the running flag is still cleared.
"""

from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_ingestion(result: dict | None = None, raise_exc: Exception | None = None):
    """
    Patch _run_ingestion so it returns *result* or raises *raise_exc*
    without touching the database or network.
    """
    if raise_exc is not None:
        mock = AsyncMock(side_effect=raise_exc)
    else:
        mock = AsyncMock(
            return_value=result
            or {
                "stories_ingested": 1,
                "comments_ingested": 10,
                "comments_skipped": 0,
                "stories_fetched": 3,
                "cycle_cap_reached": False,
            }
        )
    return patch("app.tasks.fetch_job._run_ingestion", mock)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_successful_run_clears_running_flag():
    """After a successful run the _running event must be cleared."""
    from app.tasks import fetch_job

    fetch_job._running.clear()
    with _patch_ingestion():
        fetch_job.run_fetch_job()

    assert not fetch_job._running.is_set()


def test_failed_run_still_clears_running_flag():
    """Even if the ingestion raises, _running must be cleared."""
    from app.tasks import fetch_job

    fetch_job._running.clear()
    with _patch_ingestion(raise_exc=RuntimeError("ingestion boom")):
        fetch_job.run_fetch_job()

    assert not fetch_job._running.is_set()


def test_overlap_prevention_skips_concurrent_call():
    """
    If _running is already set when run_fetch_job is called, the function
    must return immediately without starting a new ingestion cycle.
    """
    from app.tasks import fetch_job

    fetch_job._running.set()  # Simulate an in-progress run
    try:
        with _patch_ingestion() as mock_run:
            fetch_job.run_fetch_job()
            mock_run.assert_not_called()
    finally:
        fetch_job._running.clear()


def test_second_run_executes_after_first_completes():
    """Two sequential (non-overlapping) runs both complete successfully."""
    from app.tasks import fetch_job

    fetch_job._running.clear()
    with _patch_ingestion() as mock_run:
        fetch_job.run_fetch_job()
        fetch_job.run_fetch_job()
        assert mock_run.call_count == 2


def test_running_flag_set_during_execution():
    """
    The _running flag must be set for the duration of the job and cleared
    after it finishes.
    """
    from app.tasks import fetch_job

    fetch_job._running.clear()
    flag_during: list[bool] = []

    async def _spy_ingestion():
        flag_during.append(fetch_job._running.is_set())
        return {
            "stories_ingested": 0,
            "comments_ingested": 0,
            "comments_skipped": 0,
            "stories_fetched": 0,
            "cycle_cap_reached": False,
        }

    with patch("app.tasks.fetch_job._run_ingestion", _spy_ingestion):
        fetch_job.run_fetch_job()

    assert flag_during == [True], "Flag should have been set during ingestion"
    assert not fetch_job._running.is_set(), "Flag should be cleared after run"
