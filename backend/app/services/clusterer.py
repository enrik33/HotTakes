"""
Stance-bucket clustering service (Issue #25).

For each topic, groups comments by stance and runs KMeans within each bucket
so that clusters reflect coherent opinion groups rather than mixed sentiment.

Algorithm
---------
For each stance in [SUPPORT, OPPOSE, MIXED, NEUTRAL]:
  1. Query Comment JOIN Classification JOIN Embedding for the topic+stance.
  2. Deserialize embedding vectors.
  3. Guard: skip if < 2 samples (KMeans cannot run).
  4. Fit KMeans(n_clusters=min(n_clusters_per_stance, n_samples)).
  5. Delete previous Cluster rows for this topic+stance.
  6. Insert new Cluster rows with size counts.
  7. Bulk-update Comment.cluster_id.

Returns a summary dict with counts per stance.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import numpy as np

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session  # pragma: no cover

logger = logging.getLogger(__name__)

_STANCES = ("SUPPORT", "OPPOSE", "MIXED", "NEUTRAL")


def _pick_representative(
    comments: list,
    centroid: "np.ndarray",
    embedding_matrix: "np.ndarray",
) -> int | None:
    """Return the comment ID closest to *centroid* that meets min-length.

    Computes cosine similarity between each comment embedding and the
    cluster centroid.  Only considers comments whose ``body`` is at least
    ``settings.min_quote_length`` characters long.  Returns ``None`` when
    no comment passes the length gate.

    Parameters
    ----------
    comments:
        Comment ORM objects ordered the same as *embedding_matrix* rows.
    centroid:
        1-D centroid vector for the cluster (from ``KMeans.cluster_centers_``).
    embedding_matrix:
        2-D float32 array, one row per comment.
    """
    centroid_norm = np.linalg.norm(centroid)
    if centroid_norm == 0:
        return None

    best_id: int | None = None
    best_sim = -2.0

    for comment, vec in zip(comments, embedding_matrix):
        body = getattr(comment, "body", "") or ""
        if len(body) < settings.min_quote_length:
            continue
        vec_norm = np.linalg.norm(vec)
        if vec_norm == 0:
            continue
        sim = float(np.dot(vec, centroid) / (vec_norm * centroid_norm))
        if sim > best_sim:
            best_sim = sim
            best_id = comment.id

    return best_id


def run_clustering_for_topic(db: "Session", topic_id: int) -> dict:
    """Cluster comments for a single topic by stance bucket.

    Parameters
    ----------
    db:
        SQLAlchemy ``Session``.
    topic_id:
        The topic to cluster.

    Returns
    -------
    dict
        ``{"topic_id": int, "stances": {stance: {"clusters": int, "comments": int}}}``
    """
    from sqlalchemy import select, update  # noqa: PLC0415

    from app.models import Classification, Cluster, Comment, Embedding  # noqa: PLC0415

    results: dict = {"topic_id": topic_id, "stances": {}}

    for stance in _STANCES:
        # ------------------------------------------------------------------
        # 1. Fetch comments that have both a classification and an embedding
        # ------------------------------------------------------------------
        stmt = (
            select(Comment, Embedding)
            .join(Classification, Classification.comment_id == Comment.id)
            .join(Embedding, Embedding.comment_id == Comment.id)
            .where(Comment.topic_id == topic_id)
            .where(Classification.stance == stance)
            .where(Embedding.embedding_vector.isnot(None))
        )
        rows = db.execute(stmt).all()

        if len(rows) < 2:
            logger.info(
                "cluster_skip_insufficient",
                extra={
                    "event": "cluster_skip_insufficient",
                    "component": "clusterer",
                    "request_id": "-",
                    "job_name": "cluster",
                    "topic_id": topic_id,
                    "stance": stance,
                    "n_comments": len(rows),
                },
            )
            results["stances"][stance] = {"clusters": 0, "comments": len(rows)}
            continue

        comments = [r[0] for r in rows]
        embeddings_objs = [r[1] for r in rows]

        # ------------------------------------------------------------------
        # 2. Deserialize vectors
        # ------------------------------------------------------------------
        try:
            matrix = np.array(
                [json.loads(e.embedding_vector) for e in embeddings_objs],
                dtype=np.float32,
            )
        except Exception:
            logger.exception(
                "cluster_deserialize_failed",
                extra={
                    "event": "cluster_deserialize_failed",
                    "component": "clusterer",
                    "request_id": "-",
                    "job_name": "cluster",
                    "topic_id": topic_id,
                    "stance": stance,
                },
            )
            results["stances"][stance] = {"clusters": 0, "comments": len(rows)}
            continue

        n_samples = len(comments)
        n_clusters = min(settings.n_clusters_per_stance, n_samples)

        # ------------------------------------------------------------------
        # 3. Fit KMeans
        # ------------------------------------------------------------------
        from sklearn.cluster import KMeans  # noqa: PLC0415

        kmeans = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
        labels = kmeans.fit_predict(matrix)

        # ------------------------------------------------------------------
        # 4. Delete old Cluster rows for this topic+stance
        # ------------------------------------------------------------------
        old_clusters = (
            db.query(Cluster)
            .filter(Cluster.topic_id == topic_id, Cluster.stance == stance)
            .all()
        )
        old_cluster_ids = [c.id for c in old_clusters]

        if old_cluster_ids:
            # Null out cluster_id on comments that belonged to old clusters
            db.execute(
                update(Comment)
                .where(Comment.cluster_id.in_(old_cluster_ids))
                .values(cluster_id=None)
            )
            for c in old_clusters:
                db.delete(c)
            db.flush()

        # ------------------------------------------------------------------
        # 5. Insert new Cluster rows
        # ------------------------------------------------------------------
        label_to_cluster: dict[int, Cluster] = {}
        for label_idx in range(n_clusters):
            mask = labels == label_idx
            size = int(mask.sum())
            cluster = Cluster(
                topic_id=topic_id,
                stance=stance,
                cluster_label=label_idx,
                size=size,
            )
            db.add(cluster)
            label_to_cluster[label_idx] = cluster

        db.flush()  # populate cluster.id

        # ------------------------------------------------------------------
        # 6. Extract keywords per cluster and store them
        # ------------------------------------------------------------------
        from app.services.keyword_extractor import extract_keywords  # noqa: PLC0415

        label_to_texts: dict[int, list[str]] = {i: [] for i in range(n_clusters)}
        for comment, label in zip(comments, labels):
            label_to_texts[int(label)].append(comment.body)

        for label_idx, cluster in label_to_cluster.items():
            kws = extract_keywords(label_to_texts[label_idx])
            cluster.keywords = ",".join(kws)

        # ------------------------------------------------------------------
        # 7. Pick representative comment per cluster (closest to centroid)
        # ------------------------------------------------------------------
        for label_idx, cluster in label_to_cluster.items():
            mask = labels == label_idx
            cluster_comments = [c for c, m in zip(comments, mask) if m]
            cluster_matrix = matrix[mask]
            centroid = kmeans.cluster_centers_[label_idx]
            cluster.representative_comment_id = _pick_representative(
                cluster_comments, centroid, cluster_matrix
            )

        # ------------------------------------------------------------------
        # 8. Bulk-update Comment.cluster_id
        # ------------------------------------------------------------------
        for comment, label in zip(comments, labels):
            comment.cluster_id = label_to_cluster[int(label)].id

        db.flush()

        # ------------------------------------------------------------------
        # 9. Quality gate: remove clusters smaller than min_cluster_size
        # ------------------------------------------------------------------
        removed = 0
        for label_idx, cluster in list(label_to_cluster.items()):
            if cluster.size < settings.min_cluster_size:
                # Null out cluster_id on comments assigned to this cluster
                db.execute(
                    update(Comment)
                    .where(Comment.cluster_id == cluster.id)
                    .values(cluster_id=None)
                )
                db.delete(cluster)
                del label_to_cluster[label_idx]
                removed += 1

        if removed:
            db.flush()
            n_clusters -= removed

        logger.info(
            "cluster_stance_done",
            extra={
                "event": "cluster_stance_done",
                "component": "clusterer",
                "request_id": "-",
                "job_name": "cluster",
                "topic_id": topic_id,
                "stance": stance,
                "n_clusters": n_clusters,
                "n_comments": n_samples,
            },
        )
        results["stances"][stance] = {"clusters": n_clusters, "comments": n_samples}

    db.commit()
    return results
