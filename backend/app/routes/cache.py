
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ResponseCache

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.get("/stats")
def get_cache_stats(db: Session = Depends(get_db)):

    cache_records = db.query(ResponseCache).all()

    now = datetime.now(timezone.utc)

    total_entries = len(cache_records)
    valid_entries = 0
    expired_entries = 0

    for record in cache_records:

        expires_at = record.expires_at

        if expires_at is None:
            expired_entries += 1
            continue

        # SQLite may return timezone-naive datetime
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now < expires_at:
            valid_entries += 1
        else:
            expired_entries += 1

    return {
        "total_entries": total_entries,
        "valid_entries": valid_entries,
        "expired_entries": expired_entries
    }

@router.delete("/clear")
def clear_cache(db: Session = Depends(get_db)):

    deleted_count = db.query(ResponseCache).delete()

    db.commit()

    return {
        "message": "Cache cleared successfully",
        "deleted_entries": deleted_count
    }

