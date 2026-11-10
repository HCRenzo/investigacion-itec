"""Engine, session factory and schema bootstrap.

Postgres (Supabase): the schema is owned by supabase/migrations/*.sql, the app never alters it.
SQLite (local dev / tests, when DATABASE_URL is not set): tables are created from the models.
"""
import os
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from api.config import settings


class Base(DeclarativeBase):
    pass


def _engine_options(url: str) -> dict:
    if url.startswith("sqlite"):
        options = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
        return options
    options = {
        # Supabase's pooler runs in transaction mode: server-side prepared statements are not allowed.
        "connect_args": {"prepare_threshold": None},
        "pool_pre_ping": True,
    }
    if os.getenv("VERCEL"):
        options["poolclass"] = NullPool  # serverless: let the Supabase pooler do the pooling
    return options


engine = create_engine(settings.database_url, **_engine_options(settings.database_url))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

_init_lock = threading.Lock()
_initialized = False


def ensure_initialized() -> None:
    """Prepare the database once per process. Serverless hosts (Vercel) may skip ASGI lifespan,
    so every request path calls this instead of relying on startup."""
    global _initialized
    if not _initialized:
        with _init_lock:
            if not _initialized:
                init_db()
                _initialized = True


def get_db():
    ensure_initialized()
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    from api import models  # noqa: F401  (registers the tables)
    from api.container import Services

    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
    with SessionLocal() as session:
        Services(session).seed.run()
