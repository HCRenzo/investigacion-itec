"""Application settings, read once from environment variables."""
import os
from dataclasses import dataclass
from decimal import Decimal


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        # Vercel only allows writes to /tmp; define DATABASE_URL (Postgres) there for real persistence.
        return "sqlite:////tmp/tienda.db" if os.getenv("VERCEL") else "sqlite:///tienda.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    token_hours: int
    admin_email: str
    admin_password: str
    tax_rate: Decimal
    # Internal switch: which receipt engine the checkout uses ("v1" legacy, "v2" optimized).
    receipt_engine: str
    # How many redundant passes the legacy (v1) engine performs. Higher = slower.
    legacy_work_factor: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=_database_url(),
            secret_key=os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production-0000"),
            token_hours=int(os.getenv("TOKEN_HOURS", "12")),
            admin_email=os.getenv("ADMIN_EMAIL", "admin@tienda.local").lower(),
            admin_password=os.getenv("ADMIN_PASSWORD", "admin1234"),
            tax_rate=Decimal(os.getenv("TAX_RATE", "0.21")),
            receipt_engine=os.getenv("RECEIPT_ENGINE", "v2").lower(),
            legacy_work_factor=int(os.getenv("LEGACY_WORK_FACTOR", "6000")),
        )


settings = Settings.from_env()
