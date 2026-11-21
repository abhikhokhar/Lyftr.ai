import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, Base
from . import models
from .services.llm_service import API_KEYS
from .routes.chat import router as chat_router


app = FastAPI(
    title="Lyftr AI Chatbot",
    description="LLM Chatbot with Key Failover and Response Caching",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)


@app.get("/health")
def health():
    # Verify database connectivity
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "keys_configured": len(API_KEYS),
        "cache_enabled": True
    }
