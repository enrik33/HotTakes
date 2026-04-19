"""
Unit tests for the HN Firebase API client (hn_client.py).

Uses unittest.mock to avoid real network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.hn_client import HNClient, HNClientError, StoryType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data, status=200):
    """Build a mock aiohttp response context-manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.raise_for_status = MagicMock()
    if status >= 400:
        import aiohttp

        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=status
        )
    # Support `async with session.get(url) as resp:`
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Tests: context-manager lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_creates_and_closes_session():
    """HNClient creates its own session and closes it on exit."""
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_cls.return_value = mock_session

        async with HNClient():
            pass

        mock_session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: get_story_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_story_ids_top():
    """get_story_ids returns a list of ints for top stories."""
    ids = [1, 2, 3, 4, 5]
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response(ids))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_story_ids(StoryType.TOP)

    assert result == ids


@pytest.mark.asyncio
async def test_get_story_ids_ask():
    """get_story_ids uses the correct endpoint for ask stories."""
    ids = [10, 20]
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response(ids))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_story_ids(StoryType.ASK)

    assert result == ids
    called_url = mock_session.get.call_args[0][0]
    assert "askstories" in called_url


@pytest.mark.asyncio
async def test_get_story_ids_bad_response_raises():
    """get_story_ids raises HNClientError when API returns non-list."""
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response({"error": "bad"}))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            with pytest.raises(HNClientError):
                await client.get_story_ids()


# ---------------------------------------------------------------------------
# Tests: get_item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_item_returns_story():
    """get_item returns a normal story dict."""
    story = {"id": 42, "type": "story", "title": "Test Story", "score": 100}
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response(story))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_item(42)

    assert result == story


@pytest.mark.asyncio
async def test_get_item_deleted_returns_none():
    """get_item returns None for items with deleted=True."""
    item = {"id": 99, "deleted": True}
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response(item))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_item(99)

    assert result is None


@pytest.mark.asyncio
async def test_get_item_dead_returns_none():
    """get_item returns None for items with dead=True."""
    item = {"id": 77, "dead": True, "type": "comment"}
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response(item))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_item(77)

    assert result is None


@pytest.mark.asyncio
async def test_get_item_nonexistent_returns_none():
    """get_item returns None when the API returns null (item doesn't exist)."""
    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_response(None))
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_item(9999999)

    assert result is None


# ---------------------------------------------------------------------------
# Tests: retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_item_retries_on_connection_error():
    """get_item retries up to MAX_RETRIES times on connection errors."""
    import aiohttp as _aiohttp

    story = {"id": 5, "type": "story", "title": "Retry story"}

    call_count = 0

    def side_effect(url):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            cm = MagicMock()
            exc = _aiohttp.ClientConnectionError("timeout")
            cm.__aenter__ = AsyncMock(side_effect=exc)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm
        return _mock_response(story)

    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        with patch("app.services.hn_client.asyncio.sleep", new_callable=AsyncMock):
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session.get = MagicMock(side_effect=side_effect)
            mock_cls.return_value = mock_session

            async with HNClient() as client:
                result = await client.get_item(5)

    assert result == story
    assert call_count == 3


@pytest.mark.asyncio
async def test_get_item_raises_after_max_retries():
    """get_item raises HNClientError when all retries are exhausted."""
    import aiohttp as _aiohttp

    def side_effect(url):
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=_aiohttp.ClientConnectionError("down"))
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        with patch("app.services.hn_client.asyncio.sleep", new_callable=AsyncMock):
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session.get = MagicMock(side_effect=side_effect)
            mock_cls.return_value = mock_session

            async with HNClient() as client:
                with pytest.raises(HNClientError):
                    await client.get_item(1)


# ---------------------------------------------------------------------------
# Tests: get_items_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_items_batch_returns_ordered_results():
    """get_items_batch returns results in the same order as input IDs."""
    story_a = {"id": 1, "type": "story", "title": "A"}
    story_b = {"id": 2, "type": "story", "title": "B"}

    responses = {1: story_a, 2: story_b, 3: {"id": 3, "deleted": True}}

    def make_response(item_id):
        return _mock_response(responses[item_id])

    with patch("app.services.hn_client.aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(
            side_effect=lambda url: make_response(
                int(url.split("/")[-1].replace(".json", ""))
            )
        )
        mock_cls.return_value = mock_session

        async with HNClient() as client:
            result = await client.get_items_batch([1, 2, 3])

    assert result[0] == story_a
    assert result[1] == story_b
    assert result[2] is None


# ---------------------------------------------------------------------------
# Tests: without context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_raises_without_context_manager():
    """Calling _get without entering context manager raises HNClientError."""
    client = HNClient()
    with pytest.raises(HNClientError, match="context manager"):
        await client._get("https://example.com")
