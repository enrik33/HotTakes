"""
Author privacy utility.

Hashes HN usernames with SHA-256 before storage so no raw
usernames ever touch the database.
"""

import hashlib


def hash_username(username: str | None) -> str | None:
    """Return SHA-256 hex digest of username, or None if username is absent."""
    if not username:
        return None
    return hashlib.sha256(username.encode("utf-8")).hexdigest()
