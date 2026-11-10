"""Turn domain objects into the JSON the front end consumes. One place decides what each audience may see."""
from decimal import Decimal

from api.models import Order, Product, User


def _money(value) -> str:
    return f"{Decimal(value):.2f}"


class UserPresenter:
    @staticmethod
    def render(user: User) -> dict:
        return {"id": str(user.uuid), "name": user.name, "email": user.email, "role": user.role}

    @classmethod
    def session(cls, token: str, user: User) -> dict:
        return {"token": token, "user": cls.render(user)}


class ProductPresenter:
    @staticmethod
    def render(p: Product) -> dict:
        return {"id": str(p.uuid), "sku": p.sku, "name": p.name, "description": p.description,
                "category": p.category.name, "price": _money(p.price), "stock": p.stock, "active": p.is_active}

    @classmethod
    def many(cls, products) -> list[dict]:
        return [cls.render(p) for p in products]


class OrderPresenter:
    @staticmethod
    def render(o: Order, *, admin: bool = False) -> dict:
        data = {
            "number": o.number,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": [{"name": i.name, "quantity": i.quantity, "unit_price": _money(i.unit_price),
                       "line_total": _money(i.line_total)} for i in o.items],
            "item_count": o.item_count,
            "subtotal": _money(o.subtotal), "tax": _money(o.tax), "total": _money(o.total),
            "processing_seconds": float(o.processing_seconds or 0),
        }
        if admin:  # customer details and the internal engine are for staff only
            data.update(customer=o.user.name, customer_email=o.user.email, engine=o.engine)
        return data

    @classmethod
    def many(cls, orders, **kw) -> list[dict]:
        return [cls.render(o, **kw) for o in orders]


class ReportPresenter:
    @staticmethod
    def summary(s: dict) -> dict:
        return {
            "orders": s["orders"], "revenue": _money(s["revenue"]), "units": s["units"], "customers": s["customers"],
            "top_products": [{"name": n, "units": u, "revenue": _money(r)} for n, u, r in s["top_products"]],
            "low_stock": ProductPresenter.many(s["low_stock"]),
            "engines": [{"engine": e, "orders": c, "avg_seconds": round(avg, 3)} for e, c, avg in s["engines"]],
        }
