"""
Hacker News Firebase API client.

Uses the public HN Firebase REST API — no authentication required.
API docs: https://github.com/HackerNews/API
Base URL: https://hacker-news.firebaseio.com/v0/
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # seconds


class StoryType(str, Enum):
    TOP = "top"
    ASK = "ask"
    SHOW = "show"
    NEW = "new"


_STORY_TYPE_ENDPOINTS: dict[StoryType, str] = {
    StoryType.TOP: "topstories",
    StoryType.ASK: "askstories",
    StoryType.SHOW: "showstories",
    StoryType.NEW: "newstories",
}


class HNClientError(Exception):
    """Raised on unrecoverable HN API errors."""


class HNClient:
    """Async client for the Hacker News Firebase API."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "HNClient":
        if self._owns_session:
            self._session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def _get(self, url: str) -> Any:
        """GET a JSON resource with exponential-backoff retry."""
        if not self._session:
            raise HNClientError("HNClient must be used as an async context manager.")

        last_exc: Exception = HNClientError("No attempts made")
        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(url) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2**attempt)
                    logger.warning(
                        "hn_client_retry",
                        extra={
                            "url": url,
                            "attempt": attempt + 1,
                            "wait_seconds": wait,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(wait)
        raise HNClientError(
            f"Failed after {MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    async def get_story_ids(self, story_type: StoryType = StoryType.TOP) -> list[int]:
        """Return list of story IDs for the given story type (up to 500)."""
        endpoint = _STORY_TYPE_ENDPOINTS[story_type]
        url = f"{HN_BASE_URL}/{endpoint}.json"
        result = await self._get(url)
        if not isinstance(result, list):
            raise HNClientError(
                f"Unexpected response type for story IDs: {type(result)}"
            )
        return result

    async def get_item(self, item_id: int) -> Optional[dict[str, Any]]:
        """
        Fetch a single HN item (story or comment) by ID.

        Returns None if the item is deleted or dead (soft-removed by HN).
        Returns None if the item does not exist.
        """
        url = f"{HN_BASE_URL}/item/{item_id}.json"
        data = await self._get(url)
        if data is None:
            return None
        if data.get("deleted") or data.get("dead"):
            logger.debug(
                "hn_item_skipped",
                extra={
                    "item_id": item_id,
                    "deleted": data.get("deleted", False),
                    "dead": data.get("dead", False),
                },
            )
            return None
        return data

    async def get_items_batch(
        self, item_ids: list[int], concurrency: int = 20
    ) -> list[Optional[dict[str, Any]]]:
        """
        Fetch multiple items concurrently with a bounded semaphore.

        Returns a list in the same order as item_ids. Deleted/dead items are None.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _fetch(item_id: int) -> Optional[dict[str, Any]]:
            async with semaphore:
                try:
                    return await self.get_item(item_id)
                except HNClientError as exc:
                    logger.error(
                        "hn_item_fetch_error",
                        extra={"item_id": item_id, "error": str(exc)},
                    )
                    return None

        return list(await asyncio.gather(*(_fetch(iid) for iid in item_ids)))
