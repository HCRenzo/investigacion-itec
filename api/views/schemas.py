"""Request bodies (input validation)."""
import re
from decimal import Decimal
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
