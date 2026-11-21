
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from ..database import get_db
from ..models import UsageLog

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/stats")
def get_analytics_stats(db: Session = Depends(get_db)):

    total_requests = db.query(UsageLog).count()

    cache_hits = (
        db.query(UsageLog)
        .filter(UsageLog.cache_hit == True)
        .count()
    )

    cache_misses = total_requests - cache_hits

    llm_calls = (
        db.query(UsageLog)
        .filter(UsageLog.cache_hit == False)
        .count()
    )

    total_input_tokens = (
        db.query(func.sum(UsageLog.input_tokens)).scalar() or 0
    )

    total_output_tokens = (
        db.query(func.sum(UsageLog.output_tokens)).scalar() or 0
    )

    total_tokens = total_input_tokens + total_output_tokens

    average_latency = (
        db.query(func.avg(UsageLog.latency_ms)).scalar() or 0
    )

    cache_hit_rate = (
        (cache_hits / total_requests) * 100
        if total_requests > 0 else 0
    )

    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "llm_api_calls": llm_calls,
        "cache_hit_rate": round(cache_hit_rate, 2),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens_used": total_tokens,
        "average_latency_ms": round(average_latency, 2)
    }
