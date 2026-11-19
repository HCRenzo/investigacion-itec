"""Request bodies (input validation)."""
import re
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Correo electrónico inválido")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class CartLine(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=999)


class CheckoutRequest(BaseModel):
    lines: list[CartLine] = Field(min_length=1, max_length=100)


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="General", max_length=60)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0)
    active: bool = True


class SaleLine(BaseModel):
    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class SaleRequest(BaseModel):
    customer: str = Field(min_length=1, max_length=120)
    lines: list[SaleLine] = Field(min_length=1, max_length=500)


class EngineIn(BaseModel):
    receipt_engine: Literal["auto", "v1", "v2"]


class ExperimentIn(BaseModel):
    sizes: list[int] = Field(default=[10, 100, 500, 1500], min_length=1, max_length=8)
    replicates: int = Field(default=30, ge=3, le=200)
    warmup: int = Field(default=5, ge=0, le=20)
    work_factor: int = Field(default=1, ge=1, le=200)
    catalog_size: int = Field(default=200, ge=1, le=5000)
    seed: int = Field(default=2026, ge=0)
    alpha: float = Field(default=0.05, gt=0, lt=0.5)
    threshold: float = Field(default=20.0, gt=0)
    bootstrap_reps: int = Field(default=10_000, ge=200, le=50_000)

    @field_validator("sizes")
    @classmethod
    def _sizes(cls, v: list[int]) -> list[int]:
        if any(n < 1 or n > 5000 for n in v):
            raise ValueError("Cada tamaño de pedido debe estar entre 1 y 5000 líneas")
        return v


class BenchmarkIn(BaseModel):
    sizes: list[int] = Field(default=[10, 50, 100, 250, 500], min_length=2, max_length=10)
    repetitions: int = Field(default=10, ge=1, le=100)
    v1_work_factor: int = Field(default=1, ge=1, le=200)
    catalog_size: int = Field(default=200, ge=1, le=5000)
    seed: int = Field(default=2026, ge=0)


class StatRow(BaseModel):
    engine: Literal["v1", "v2"]
    lines: int = Field(ge=0)
    seconds: float = Field(ge=0)


class StatisticsIn(BaseModel):
    source: Literal["orders", "samples"] = "orders"
    samples: list[StatRow] = Field(default=[], max_length=20000)
    alpha: float = Field(default=0.05, gt=0, lt=0.5)
    threshold: float = Field(default=20.0, gt=0)
