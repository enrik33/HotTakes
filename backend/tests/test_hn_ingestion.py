"""
Tests for M2 ingestion utilities and HNIngestionService.

Covers:
  - author_hash.hash_username
  - keyword_filter.story_matches_scope / extract_target_entities
  - HNIngestionService (in-memory SQLite + mock HNClient)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Comment, Post, Topic
from app.services.author_hash import hash_username
from app.services.hn_client import StoryType
from app.services.hn_ingestion import HNIngestionService
from app.services.keyword_filter import extract_target_entities, story_matches_scope


# ---------------------------------------------------------------------------
# DB fixture (in-memory SQLite)
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Mock HN client
# ---------------------------------------------------------------------------


class MockHNClient:
    """Minimal async mock that returns pre-loaded story/comment data."""

    def __init__(
        self,
        story_ids: dict[StoryType, list[int]] | None = None,
        items: dict[int, dict | None] | None = None,
    ) -> None:
        self._story_ids = story_ids or {}
        self._items = items or {}

    async def get_story_ids(self, story_type: StoryType) -> list[int]:
        return self._story_ids.get(story_type, [])

    async def get_items_batch(
        self, item_ids: list[int], concurrency: int = 20
    ) -> list[dict | None]:
        return [self._items.get(i) for i in item_ids]


# ---------------------------------------------------------------------------
# author_hash
# ---------------------------------------------------------------------------


class TestAuthorHash:
    def test_hash_returns_64_char_hex(self):
        result = hash_username("pg")
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_is_deterministic(self):
        assert hash_username("dang") == hash_username("dang")

    def test_different_usernames_produce_different_hashes(self):
        assert hash_username("alice") != hash_username("bob")

    def test_none_returns_none(self):
        assert hash_username(None) is None

    def test_empty_string_returns_none(self):
        assert hash_username("") is None


# ---------------------------------------------------------------------------
# keyword_filter — story_matches_scope
# ---------------------------------------------------------------------------


class TestStoryMatchesScope:
    def test_ask_hn_always_matches(self):
        assert story_matches_scope("Ask HN: Should we regulate AI?")

    def test_show_hn_always_matches(self):
        assert story_matches_scope("Show HN: My new Rust CLI tool")

    def test_ai_keyword_matches(self):
        assert story_matches_scope("OpenAI releases new GPT model")

    def test_engineering_keyword_matches(self):
        assert story_matches_scope("Why we migrated from MySQL to Postgres")

    def test_industry_keyword_matches(self):
        assert story_matches_scope("Microsoft acquires startup for $2B")

    def test_unrelated_title_does_not_match(self):
        assert not story_matches_scope("Local bakery wins best croissant award")

    def test_case_insensitive(self):
        assert story_matches_scope("THE RISE OF MACHINE LEARNING")

    def test_extra_terms_extend_scope(self):
        assert story_matches_scope("FooBaz raises $10M", extra_terms=["FooBaz"])

    def test_extra_terms_alone_not_matched_without_term(self):
        assert not story_matches_scope("FooBaz raises $10M")


# ---------------------------------------------------------------------------
# keyword_filter — extract_target_entities
# ---------------------------------------------------------------------------


class TestExtractTargetEntities:
    def test_known_entity_extracted(self):
        entities = extract_target_entities("OpenAI releases GPT-5")
        assert "OpenAI" in entities or "GPT-5" in entities

    def test_result_is_list(self):
        result = extract_target_entities("Some title")
        assert isinstance(result, list)

    def test_max_10_entities(self):
        title = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda"
        result = extract_target_entities(title)
        assert len(result) <= 10

    def test_empty_title_returns_empty(self):
        assert extract_target_entities("") == []

    def test_no_duplicates(self):
        result = extract_target_entities("React vs React: the React debate")
        assert len(result) == len(set(r.lower() for r in result))


# ---------------------------------------------------------------------------
# HNIngestionService — helper builders
# ---------------------------------------------------------------------------


def _make_story(
    item_id: int = 1001,
    title: str = "OpenAI releases a new LLM model for developers",
    score: int = 200,
    descendants: int = 150,
    kids: list[int] | None = None,
    by: str | None = "pg",
) -> dict:
    return {
        "id": item_id,
        "type": "story",
        "title": title,
        "score": score,
        "descendants": descendants,
        "kids": kids or [],
        "by": by,
        "time": 1_700_000_000,
    }


def _make_comment(
    item_id: int,
    text: str = "This is a thoughtful comment.",
    parent: int = 1001,
    by: str | None = "dang",
    kids: list[int] | None = None,
) -> dict:
    return {
        "id": item_id,
        "type": "comment",
        "text": text,
        "parent": parent,
        "by": by,
        "time": 1_700_001_000,
        "kids": kids or [],
    }


# ---------------------------------------------------------------------------
# HNIngestionService — tests
# ---------------------------------------------------------------------------


class TestHNIngestionService:
    @pytest.mark.asyncio
    async def test_matching_story_creates_topic_and_post(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=1001, descendants=100)
        client = MockHNClient(
            story_ids={StoryType.TOP: [1001], StoryType.ASK: [], StoryType.SHOW: []},
            items={1001: story},
        )
        service = HNIngestionService(db=db, client=client)
        result = await service.run()

        assert result["stories_ingested"] == 1
        assert db.query(Topic).count() == 1
        assert db.query(Post).count() == 1

    @pytest.mark.asyncio
    async def test_post_has_correct_fields(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=2001, score=500)
        client = MockHNClient(
            story_ids={StoryType.TOP: [2001], StoryType.ASK: [], StoryType.SHOW: []},
            items={2001: story},
        )
        await HNIngestionService(db=db, client=client).run()

        post = db.query(Post).first()
        assert post.external_id == "2001"
        assert post.platform == "hackernews"
        assert post.score == 500
        assert post.author_hash == hash_username("pg")
        assert "https://news.ycombinator.com/item?id=2001" in post.permalink

    @pytest.mark.asyncio
    async def test_story_below_comment_threshold_skipped(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 100
        )

        story = _make_story(item_id=3001, descendants=10)  # below threshold
        client = MockHNClient(
            story_ids={StoryType.TOP: [3001], StoryType.ASK: [], StoryType.SHOW: []},
            items={3001: story},
        )
        result = await HNIngestionService(db=db, client=client).run()

        assert result["stories_ingested"] == 0
        assert db.query(Topic).count() == 0

    @pytest.mark.asyncio
    async def test_story_without_keywords_skipped(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(
            item_id=4001,
            title="Local bakery wins best croissant award",
            descendants=200,
        )
        client = MockHNClient(
            story_ids={StoryType.TOP: [4001], StoryType.ASK: [], StoryType.SHOW: []},
            items={4001: story},
        )
        result = await HNIngestionService(db=db, client=client).run()

        assert result["stories_ingested"] == 0

    @pytest.mark.asyncio
    async def test_ask_hn_story_always_ingested(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(
            item_id=5001,
            title="Ask HN: What is your favourite non-tech hobby?",
            descendants=80,
        )
        client = MockHNClient(
            story_ids={StoryType.TOP: [], StoryType.ASK: [5001], StoryType.SHOW: []},
            items={5001: story},
        )
        result = await HNIngestionService(db=db, client=client).run()

        assert result["stories_ingested"] == 1

    @pytest.mark.asyncio
    async def test_comments_ingested(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )
        monkeypatch.setattr("app.services.hn_ingestion.app_settings.hn_max_depth", 2)

        story = _make_story(item_id=6001, kids=[6002, 6003], descendants=80)
        c1 = _make_comment(6002, parent=6001)
        c2 = _make_comment(6003, parent=6001)
        client = MockHNClient(
            story_ids={StoryType.TOP: [6001], StoryType.ASK: [], StoryType.SHOW: []},
            items={6001: story, 6002: c1, 6003: c2},
        )
        result = await HNIngestionService(db=db, client=client).run()

        assert result["comments_ingested"] == 2
        assert db.query(Comment).count() == 2

    @pytest.mark.asyncio
    async def test_comment_author_is_hashed(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=7001, kids=[7002], descendants=80)
        comment = _make_comment(7002, by="tptacek", parent=7001)
        client = MockHNClient(
            story_ids={StoryType.TOP: [7001], StoryType.ASK: [], StoryType.SHOW: []},
            items={7001: story, 7002: comment},
        )
        await HNIngestionService(db=db, client=client).run()

        stored = db.query(Comment).first()
        assert stored.author_hash == hash_username("tptacek")
        assert stored.author_hash != "tptacek"

    @pytest.mark.asyncio
    async def test_idempotent_story_upsert(self, db, monkeypatch):
        """Running ingestion twice on the same story must not create duplicates."""
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=8001, descendants=80)
        client = MockHNClient(
            story_ids={StoryType.TOP: [8001], StoryType.ASK: [], StoryType.SHOW: []},
            items={8001: story},
        )

        await HNIngestionService(db=db, client=client).run()
        await HNIngestionService(db=db, client=client).run()

        assert db.query(Topic).count() == 1
        assert db.query(Post).count() == 1

    @pytest.mark.asyncio
    async def test_idempotent_comment_upsert(self, db, monkeypatch):
        """Re-ingesting the same comment must not create a duplicate row."""
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=9001, kids=[9002], descendants=80)
        comment = _make_comment(9002, parent=9001)
        client = MockHNClient(
            story_ids={StoryType.TOP: [9001], StoryType.ASK: [], StoryType.SHOW: []},
            items={9001: story, 9002: comment},
        )

        await HNIngestionService(db=db, client=client).run()
        await HNIngestionService(db=db, client=client).run()

        assert db.query(Comment).count() == 1

    @pytest.mark.asyncio
    async def test_empty_body_comment_skipped(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=10001, kids=[10002], descendants=80)
        comment = _make_comment(10002, text="   ", parent=10001)  # whitespace-only
        client = MockHNClient(
            story_ids={StoryType.TOP: [10001], StoryType.ASK: [], StoryType.SHOW: []},
            items={10001: story, 10002: comment},
        )
        result = await HNIngestionService(db=db, client=client).run()

        assert result["comments_ingested"] == 0
        assert db.query(Comment).count() == 0

    @pytest.mark.asyncio
    async def test_max_comments_per_fetch_cap(self, db, monkeypatch):
        """Cycle cap stops ingestion after max_comments_per_fetch new comments."""
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.max_comments_per_fetch", 2
        )
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.max_comments_per_post", 1000
        )
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.max_comments_per_topic", 25000
        )

        story = _make_story(item_id=11001, kids=[11002, 11003, 11004], descendants=80)
        comments = {
            11002: _make_comment(11002, parent=11001),
            11003: _make_comment(11003, parent=11001),
            11004: _make_comment(11004, parent=11001),
        }
        client = MockHNClient(
            story_ids={StoryType.TOP: [11001], StoryType.ASK: [], StoryType.SHOW: []},
            items={11001: story, **comments},
        )
        await HNIngestionService(db=db, client=client).run()

        assert db.query(Comment).count() <= 2

    @pytest.mark.asyncio
    async def test_max_comments_per_post_cap(self, db, monkeypatch):
        """Per-post cap limits how many comments are ingested for a single story."""
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.max_comments_per_post", 2
        )
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.max_comments_per_fetch", 10000
        )
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.max_comments_per_topic", 25000
        )

        story = _make_story(item_id=12001, kids=[12002, 12003, 12004], descendants=80)
        comments = {
            12002: _make_comment(12002, parent=12001),
            12003: _make_comment(12003, parent=12001),
            12004: _make_comment(12004, parent=12001),
        }
        client = MockHNClient(
            story_ids={StoryType.TOP: [12001], StoryType.ASK: [], StoryType.SHOW: []},
            items={12001: story, **comments},
        )
        await HNIngestionService(db=db, client=client).run()

        assert db.query(Comment).count() <= 2

    @pytest.mark.asyncio
    async def test_depth_limit_prevents_deep_recursion(self, db, monkeypatch):
        """Comments deeper than hn_max_depth are not fetched."""
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )
        monkeypatch.setattr("app.services.hn_ingestion.app_settings.hn_max_depth", 1)

        # depth 0 comment (kid of story)
        story = _make_story(item_id=13001, kids=[13002], descendants=80)
        # depth 1 comment (kid of 13002) — should NOT be ingested with max_depth=1
        c1 = _make_comment(13002, parent=13001, kids=[13003])
        c2 = _make_comment(13003, parent=13002)
        client = MockHNClient(
            story_ids={StoryType.TOP: [13001], StoryType.ASK: [], StoryType.SHOW: []},
            items={13001: story, 13002: c1, 13003: c2},
        )
        await HNIngestionService(db=db, client=client).run()

        # Only the depth-0 comment (13002) should be stored
        assert db.query(Comment).count() == 1
        assert db.query(Comment).first().external_id == "13002"

    @pytest.mark.asyncio
    async def test_target_terms_stored_on_post(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(
            item_id=14001, title="Why React is better than Vue", descendants=80
        )
        client = MockHNClient(
            story_ids={StoryType.TOP: [14001], StoryType.ASK: [], StoryType.SHOW: []},
            items={14001: story},
        )
        await HNIngestionService(db=db, client=client).run()

        post = db.query(Post).first()
        assert post.target_terms is not None
        # React and Vue should both be extracted
        terms = post.target_terms.lower()
        assert "react" in terms or "vue" in terms

    @pytest.mark.asyncio
    async def test_anonymous_comment_author_stored_as_none(self, db, monkeypatch):
        monkeypatch.setattr(
            "app.services.hn_ingestion.app_settings.min_comments_threshold", 5
        )

        story = _make_story(item_id=15001, kids=[15002], descendants=80)
        comment = _make_comment(15002, by=None, parent=15001)  # anonymous
        client = MockHNClient(
            story_ids={StoryType.TOP: [15001], StoryType.ASK: [], StoryType.SHOW: []},
            items={15001: story, 15002: comment},
        )
        await HNIngestionService(db=db, client=client).run()

        stored = db.query(Comment).first()
        assert stored.author_hash is None
