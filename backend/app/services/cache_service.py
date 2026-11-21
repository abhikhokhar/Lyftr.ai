import hashlib
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from ..models import ResponseCache

CACHE_TTL_HOURS = 24


def generate_cache_key(messages: list, model: str) -> str:

    cache_data = {
        "messages": messages,
        "model": model
    }

    serialized_data = json.dumps(
        cache_data,
        sort_keys=True
    )

    return hashlib.sha256(
        serialized_data.encode("utf-8")
    ).hexdigest()


def get_cached_response(db: Session, cache_key: str):

    cached = (
        db.query(ResponseCache)
        .filter(ResponseCache.cache_key == cache_key)
        .first()
    )

    if not cached:
        return None

    now = datetime.now(timezone.utc)

    expires_at = cached.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now >= expires_at:
        db.delete(cached)
        db.commit()

        print("Cached response expired.")

        return None

    print("Valid cached response found.")

    return {
        "reply": cached.response,
        "metadata": (
            json.loads(cached.metadata_json)
            if cached.metadata_json else {}
        )
    }


def save_cached_response(
    db: Session,
    cache_key: str,
    response: str,
    metadata: dict
):

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(hours=CACHE_TTL_HOURS)

    cached = ResponseCache(
        cache_key=cache_key,
        response=response,
        metadata_json=json.dumps(metadata),
        expires_at=expires_at
    )

    db.add(cached)
    db.commit()

    print("Response saved in cache.")
