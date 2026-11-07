"""Engine, session factory and schema bootstrap."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from api.config import settings


class Base(DeclarativeBase):
    pass


_kwargs = {}
if settings.database_url.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        _kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, pool_pre_ping=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Columns added after the first release: (table, column, DDL type with default).
_LATE_COLUMNS = [
    ("orders", "engine", "VARCHAR(10) DEFAULT 'v2'"),
    ("orders", "processing_seconds", "FLOAT DEFAULT 0"),
]


def get_db():
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    from api import models  # noqa: F401  (registers the tables)
    from api.repositories.product import ProductRepository
    from api.repositories.user import UserRepository
    from api.services.auth_service import AuthService
    from api.services.seed_service import SeedService
    from api.services.security import PasswordHasher, TokenService

    Base.metadata.create_all(engine)
    _add_missing_columns()
    with SessionLocal() as session:
        auth = AuthService(UserRepository(session), PasswordHasher(), TokenService(settings))
        SeedService(ProductRepository(session), auth, settings).run()


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in _LATE_COLUMNS:
            if column not in {c["name"] for c in inspector.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
