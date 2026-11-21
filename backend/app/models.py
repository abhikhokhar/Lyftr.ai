
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from .database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    session_id = Column(String(128), nullable=False, index=True)

    role = Column(String, nullable=False)

    content = Column(Text, nullable=False)

    metadata_json = Column("metadata", Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

class ResponseCache(Base):
    __tablename__ = "response_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, nullable=False, index=True)
    response = Column(Text, nullable=False)
    metadata_json = Column("metadata", Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False
    )

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(128), nullable=False, index=True)

    cache_hit = Column(Boolean, nullable=False, default=False)

    model = Column(String(128), nullable=False)

    input_tokens = Column(Integer, nullable=False, default=0)

    output_tokens = Column(Integer, nullable=False, default=0)

    latency_ms = Column(Integer, nullable=False, default=0)

    resolution_source = Column(String(50), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

