"""Application settings, read once from environment variables."""
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:  # load a local .env if present (real environment variables always win)
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass


def _clean(url: str) -> str:
    """Drop query params psycopg does not understand (e.g. ?pgbouncer=true copied from Prisma examples)."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in {"pgbouncer", "connection_limit", "schema"}]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip().strip('"').strip("'")
    if not url:
        # Vercel only allows writes to /tmp; define DATABASE_URL (Postgres) there for real persistence.
        return "sqlite:////tmp/tienda.db" if os.getenv("VERCEL") else "sqlite:///tienda.db"
    if url.startswith("postgres://"):
        return _clean(url.replace("postgres://", "postgresql+psycopg://", 1))
    if url.startswith("postgresql://"):
        return _clean(url.replace("postgresql://", "postgresql+psycopg://", 1))
    return _clean(url) if url.startswith("postgresql") else url


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    token_hours: int
    admin_email: str
    admin_password: str
    tax_rate: Decimal
    seed_demo_customer: bool
    demo_customer_email: str
    demo_customer_password: str
    # Internal switch: which receipt engine the checkout uses ("v1" legacy, "v2" optimized).
    # None = take it from t_parametro (MOTOR_RECIBO). An explicit env var always wins.
    receipt_engine: str | None
    # How many redundant passes the legacy (v1) engine performs. Higher = slower.
    legacy_work_factor: int
    # Target duration (seconds) for v1. v1 measures its own speed in each request and sizes its wasteful passes
    # to land near this time, whatever the CPU or database latency. None (LEGACY_TARGET_SECONDS=0) = fixed factor.
    legacy_target_seconds: float | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=_database_url(),
            secret_key=os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production-0000"),
            token_hours=int(os.getenv("TOKEN_HOURS", "12")),
            admin_email=os.getenv("ADMIN_EMAIL", "admin@tienda.local").lower(),
            admin_password=os.getenv("ADMIN_PASSWORD", "admin1234"),
            tax_rate=Decimal(os.getenv("TAX_RATE", "0.21")),
            # Convenience account used by the pre-filled login. Set SEED_DEMO_CUSTOMER=0 in production.
            seed_demo_customer=os.getenv("SEED_DEMO_CUSTOMER", "1") != "0",
            demo_customer_email=os.getenv("DEMO_CUSTOMER_EMAIL", "cliente@prueba.com").lower(),
            demo_customer_password=os.getenv("DEMO_CUSTOMER_PASSWORD", "cliente1234"),
            receipt_engine=(os.getenv("RECEIPT_ENGINE") or "").lower() or None,
            legacy_work_factor=int(os.getenv("LEGACY_WORK_FACTOR", "550")),
            legacy_target_seconds=float(os.getenv("LEGACY_TARGET_SECONDS", "25")) or None,
        )


settings = Settings.from_env()
