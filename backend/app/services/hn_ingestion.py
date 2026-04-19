"""
HN Ingestion Service.

Fetches stories and comments from the HN Firebase API and persists them to the
database.  Each HN story that passes keyword + comment-count filtering becomes
one Topic + one Post.  Comments are ingested recursively up to hn_max_depth.

Volume caps (all configurable via settings):
  - max_comments_per_fetch  — total new comments per scheduler run
  - max_comments_per_post   — comments per HN story
  - max_comments_per_topic  — cumulative comments per Topic row
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.models import Comment, Post, Topic
from app.services.author_hash import hash_username
from app.services.hn_client import HNClient, StoryType
from app.services.keyword_filter import extract_target_entities, story_matches_scope

logger = logging.getLogger(__name__)

_STORY_TYPES = [StoryType.TOP, StoryType.ASK, StoryType.SHOW]

# Number of candidate story IDs fetched per story-type per cycle.
# Each candidate requires one API call to read its metadata (title, descendants).
MAX_CANDIDATES_PER_TYPE = 100


def _utcnow_ts() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


class IngestionResult:
    """Collects metrics for one ingestion cycle."""

    def __init__(self) -> None:
        self.stories_fetched: int = 0
        self.stories_ingested: int = 0
        self.comments_ingested: int = 0
        self.cycle_cap_reached: bool = False

    def to_dict(self) -> dict:
        return {
            "stories_fetched": self.stories_fetched,
            "stories_ingested": self.stories_ingested,
            "comments_ingested": self.comments_ingested,
            "cycle_cap_reached": self.cycle_cap_reached,
        }


class HNIngestionService:
    """Ingests HN stories and comments into the database."""

    def __init__(self, db: Session, client: HNClient) -> None:
        self.db = db
        self.client = client
        self._cycle_comment_count: int = 0  # Running total for this cycle

    async def run(self) -> dict:
        """Run one full ingestion cycle (top + ask + show stories)."""
        result = IngestionResult()

        for story_type in _STORY_TYPES:
            if self._cycle_comment_count >= app_settings.max_comments_per_fetch:
                result.cycle_cap_reached = True
                break

            ids = await self.client.get_story_ids(story_type)
            candidate_ids = ids[:MAX_CANDIDATES_PER_TYPE]
            stories = await self.client.get_items_batch(candidate_ids)

            for story in stories:
                if story is None:
                    continue

                result.stories_fetched += 1

                if not self._passes_filter(story):
                    continue

                try:
                    topic, post = self._upsert_story(story, story_type)
                    added = await self._ingest_comments(
                        kids=story.get("kids") or [],
                        topic=topic,
                        post=post,
                        depth=0,
                    )
                    self.db.commit()
                    result.stories_ingested += 1
                    result.comments_ingested += added

                except Exception:
                    self.db.rollback()
                    logger.exception(
                        "story_ingest_failed",
                        extra={
                            "event": "story_ingest_failed",
                            "component": "ingestion",
                            "request_id": "-",
                            "job_name": "fetch_hn",
                            "story_id": story.get("id"),
                        },
                    )

                if self._cycle_comment_count >= app_settings.max_comments_per_fetch:
                    result.cycle_cap_reached = True
                    break

        logger.info(
            "ingestion_cycle_complete",
            extra={
                "event": "ingestion_cycle_complete",
                "component": "ingestion",
                "request_id": "-",
                "job_name": "fetch_hn",
                **result.to_dict(),
            },
        )
        return result.to_dict()

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _passes_filter(self, story: dict) -> bool:
        """Return True if the story passes keyword and comment-count gates."""
        title = story.get("title") or ""
        num_comments = story.get("descendants") or 0
        return (
            num_comments >= app_settings.min_comments_threshold
            and story_matches_scope(title)
        )

    # ------------------------------------------------------------------
    # Story upsert
    # ------------------------------------------------------------------

    def _upsert_story(self, story: dict, story_type: StoryType) -> tuple[Topic, Post]:
        """Get-or-create a Topic + Post pair for a HN story."""
        external_id = str(story["id"])
        title = (story.get("title") or "")[:255]
        target_entities = extract_target_entities(title)

        # Check whether this story has been ingested before
        existing_post = (
            self.db.query(Post)
            .filter_by(platform="hackernews", external_id=external_id)
            .first()
        )

        if existing_post is not None:
            # Update mutable fields — score and target_terms can change
            existing_post.score = story.get("score") or 0
            existing_post.last_processed_utc = _utcnow_ts()
            existing_post.target_terms = ",".join(target_entities)
            self.db.flush()
            topic = self.db.query(Topic).filter_by(id=existing_post.topic_id).first()
            return topic, existing_post

        # New story — create Topic first (one topic per HN story in MVP)
        topic_name = title
        # Guard against the rare case where two stories share a truncated title
        if self.db.query(Topic).filter_by(name=topic_name).first() is not None:
            topic_name = f"{title[:240]} (#{external_id})"

        topic = Topic(
            name=topic_name,
            description=f"HN {story_type.value} story — item {external_id}",
        )
        self.db.add(topic)
        self.db.flush()  # Populate topic.id before creating Post

        post = Post(
            topic_id=topic.id,
            external_id=external_id,
            platform="hackernews",
            title=title,
            selftext=story.get("text") or "",
            author_hash=hash_username(story.get("by")),
            score=story.get("score") or 0,
            created_utc=story.get("time") or 0,
            permalink=f"https://news.ycombinator.com/item?id={external_id}",
            last_processed_utc=_utcnow_ts(),
            target_terms=",".join(target_entities),
        )
        self.db.add(post)
        self.db.flush()
        return topic, post

    # ------------------------------------------------------------------
    # Comment ingestion
    # ------------------------------------------------------------------

    async def _ingest_comments(
        self,
        kids: list[int],
        topic: Topic,
        post: Post,
        depth: int,
    ) -> int:
        """Recursively ingest one level of a comment thread. Returns new-comment count."""
        if not kids:
            return 0
        if depth >= app_settings.hn_max_depth:
            return 0
        if self._cycle_comment_count >= app_settings.max_comments_per_fetch:
            return 0

        # Per-topic cap
        topic_count = (
            self.db.query(func.count(Comment.id))
            .filter(Comment.topic_id == topic.id)
            .scalar()
            or 0
        )
        topic_remaining = app_settings.max_comments_per_topic - topic_count
        if topic_remaining <= 0:
            return 0

        # Per-post cap
        post_count = (
            self.db.query(func.count(Comment.id))
            .filter(Comment.post_id == post.id)
            .scalar()
            or 0
        )
        post_remaining = app_settings.max_comments_per_post - post_count
        if post_remaining <= 0:
            return 0

        cycle_remaining = (
            app_settings.max_comments_per_fetch - self._cycle_comment_count
        )
        batch_limit = min(len(kids), topic_remaining, post_remaining, cycle_remaining)
        batch = kids[:batch_limit]

        items = await self.client.get_items_batch(batch)
        added = 0

        for item in items:
            if item is None:
                continue
            if item.get("type") != "comment":
                continue

            comment = self._upsert_comment(item, topic, post)
            if comment is not None:
                added += 1
                self._cycle_comment_count += 1

            # Recurse into children even if this comment was a duplicate,
            # because its replies may be new.
            child_kids = item.get("kids") or []
            if child_kids and depth + 1 < app_settings.hn_max_depth:
                child_added = await self._ingest_comments(
                    kids=child_kids,
                    topic=topic,
                    post=post,
                    depth=depth + 1,
                )
                added += child_added

        return added

    def _upsert_comment(
        self, item: dict, topic: Topic, post: Post
    ) -> Optional[Comment]:
        """
        Insert a new comment or refresh an existing one.

        Returns the newly-created Comment, or None if the comment already
        existed or had no body (empty/deleted body).
        """
        external_id = str(item["id"])
        body = item.get("text") or ""
        if not body.strip():
            return None

        existing = (
            self.db.query(Comment)
            .filter_by(platform="hackernews", external_id=external_id)
            .first()
        )

        if existing is not None:
            # Refresh score (HN can update it over time)
            existing.score = item.get("score") or 0
            self.db.flush()
            return None  # Not a new insertion

        parent_id = item.get("parent")
        comment = Comment(
            topic_id=topic.id,
            post_id=post.id,
            external_id=external_id,
            platform="hackernews",
            body=body,
            author_hash=hash_username(item.get("by")),
            score=item.get("score") or 0,
            created_utc=item.get("time") or 0,
            parent_comment_id=str(parent_id) if parent_id else None,
            permalink=f"https://news.ycombinator.com/item?id={external_id}",
        )
        self.db.add(comment)
        self.db.flush()
        return comment
