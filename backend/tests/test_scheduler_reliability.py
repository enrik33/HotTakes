"""Tests for scheduler retry/backoff hardening (Issue #45)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, call, patch


os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scheduler.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

# Import after env vars are set
from app.tasks.scheduler import _MAX_ATTEMPTS, _RETRY_DELAYS, _run_job  # noqa: E402


class TestRunJobRetry:
    """_run_job should retry transient failures with backoff."""

    def test_succeeds_on_first_attempt(self):
        fn = MagicMock()
        with patch("app.tasks.scheduler.time.sleep") as mock_sleep:
            _run_job("test_job", "test", fn)

        fn.assert_called_once()
        mock_sleep.assert_not_called()

    def test_retries_on_transient_failure_and_succeeds(self):
        """Fails once then succeeds — should be called twice, sleep once."""
        fn = MagicMock(side_effect=[ValueError("transient"), None])
        with patch("app.tasks.scheduler.time.sleep") as mock_sleep:
            _run_job("test_job", "test", fn)

        assert fn.call_count == 2
        mock_sleep.assert_called_once_with(_RETRY_DELAYS[0])

    def test_retries_twice_then_succeeds(self):
        """Fails twice then succeeds — called 3 times, slept with first two delays."""
        fn = MagicMock(side_effect=[RuntimeError("err1"), RuntimeError("err2"), None])
        with patch("app.tasks.scheduler.time.sleep") as mock_sleep:
            _run_job("test_job", "test", fn)

        assert fn.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(_RETRY_DELAYS[0]), call(_RETRY_DELAYS[1])])

    def test_all_attempts_exhausted_logs_failure(self):
        """All 4 attempts fail — logs job_failed, does not raise."""
        fn = MagicMock(side_effect=RuntimeError("permanent"))
        with (
            patch("app.tasks.scheduler.time.sleep"),
            patch("app.tasks.scheduler.logger") as mock_logger,
        ):
            _run_job("test_job", "test", fn)  # must not raise

        assert fn.call_count == _MAX_ATTEMPTS
        # Verify job_failed and job_metrics(success=False) were logged
        logged_events = [
            call_args.kwargs.get("extra", {}).get("event")
            or (call_args.args[0] if call_args.args else None)
            for call_args in mock_logger.exception.call_args_list
            + mock_logger.error.call_args_list
        ]
        assert "job_failed" in logged_events

    def test_job_metrics_logged_on_success(self):
        fn = MagicMock()
        with patch("app.tasks.scheduler.logger") as mock_logger:
            _run_job("metrics_job", "test", fn)

        metrics_calls = [
            call_args
            for call_args in mock_logger.info.call_args_list
            if call_args.kwargs.get("extra", {}).get("event") == "job_metrics"
        ]
        assert len(metrics_calls) == 1
        extra = metrics_calls[0].kwargs["extra"]
        assert extra["success"] is True
        assert extra["attempts"] == 1
        assert "duration_s" in extra

    def test_job_metrics_logged_on_failure(self):
        fn = MagicMock(side_effect=RuntimeError("boom"))
        with (
            patch("app.tasks.scheduler.time.sleep"),
            patch("app.tasks.scheduler.logger") as mock_logger,
        ):
            _run_job("fail_job", "test", fn)

        metrics_calls = [
            call_args
            for call_args in mock_logger.error.call_args_list
            if call_args.kwargs.get("extra", {}).get("event") == "job_metrics"
        ]
        assert len(metrics_calls) == 1
        extra = metrics_calls[0].kwargs["extra"]
        assert extra["success"] is False
        assert extra["attempts"] == _MAX_ATTEMPTS

    def test_backoff_delays_are_increasing(self):
        """Verify the delay sequence is strictly increasing."""
        assert all(
            _RETRY_DELAYS[i] < _RETRY_DELAYS[i + 1]
            for i in range(len(_RETRY_DELAYS) - 1)
        )

    def test_max_attempts_matches_retry_delays(self):
        """_MAX_ATTEMPTS must equal len(_RETRY_DELAYS) + 1 (first free attempt)."""
        assert _MAX_ATTEMPTS == len(_RETRY_DELAYS) + 1


class TestStartSchedulerJobConfig:
    """Verify max_instances=1 is set on all overlap-sensitive jobs."""

    def test_cluster_and_stats_jobs_have_max_instances(self):
        """Confirm max_instances=1 is passed to cluster and stats add_job calls."""
        from apscheduler.schedulers.background import BackgroundScheduler

        mock_scheduler = MagicMock(spec=BackgroundScheduler)
        mock_scheduler.running = False

        with (
            patch("app.tasks.scheduler.scheduler", mock_scheduler),
            patch("app.tasks.fetch_job.run_fetch_job"),
        ):
            from app.tasks.scheduler import start_scheduler

            start_scheduler()

        job_kwargs_by_id = {}
        for c in mock_scheduler.add_job.call_args_list:
            job_id = c.kwargs.get("id") or (c.args[2] if len(c.args) > 2 else None)
            job_kwargs_by_id[job_id] = c.kwargs

        assert job_kwargs_by_id.get("cluster", {}).get("max_instances") == 1
        assert job_kwargs_by_id.get("stats", {}).get("max_instances") == 1
        assert job_kwargs_by_id.get("classify", {}).get("max_instances") == 1
