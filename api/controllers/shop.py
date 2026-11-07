from fastapi import APIRouter, Depends

from api.container import Services
from api.controllers.deps import current_user, get_services
from api.models import User
from api.views.presenters import OrderPresenter, ProductPresenter
from api.views.schemas import CheckoutRequest

router = APIRouter(prefix="/api")


@router.get("/products")
def list_products(services: Services = Depends(get_services)):
    return ProductPresenter.many(services.catalog.storefront())


@router.post("/orders", status_code=201)
def checkout(body: CheckoutRequest, user: User = Depends(current_user), services: Services = Depends(get_services)):
    order = services.checkout.checkout(user, [(l.product_id, l.quantity) for l in body.lines])
    return OrderPresenter.render(order)


@router.get("/orders")
def my_orders(user: User = Depends(current_user), services: Services = Depends(get_services)):
    return OrderPresenter.many(services.checkout.history(user))
