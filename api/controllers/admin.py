from uuid import UUID

from fastapi import APIRouter, Depends

from api.container import Services
from api.controllers.deps import admin_user, get_services
from api.views.presenters import OrderPresenter, ProductPresenter, ReportPresenter, UserPresenter
from api.views.schemas import EngineIn, LoginRequest, ProductIn

public = APIRouter(prefix="/api/admin")  # login only; everything else requires an admin token
router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_user)])


@public.post("/login")
def admin_login(body: LoginRequest, services: Services = Depends(get_services)):
    return UserPresenter.session(*services.auth.login_admin(body.email, body.password))


@router.get("/config")
def active_config(services: Services = Depends(get_services)):
    """Which receipt engine THIS deployment uses. Staff only: customers never see it."""
    return services.config.describe()


@router.put("/config")
def change_engine(body: EngineIn, services: Services = Depends(get_services)):
    """Switch the receipt engine from the panel: 'v1', 'v2', or 'auto' (follow this deployment's environment)."""
    services.config.set_mode(body.receipt_engine)
    return services.config.describe()


@router.get("/summary")
def summary(services: Services = Depends(get_services)):
    return ReportPresenter.summary(services.reports.summary())


@router.get("/orders")
def all_orders(limit: int = 100, services: Services = Depends(get_services)):
    return OrderPresenter.many(services.reports.recent_orders(limit), admin=True)


@router.get("/products")
def all_products(services: Services = Depends(get_services)):
    return ProductPresenter.many(services.catalog.inventory())


@router.post("/products", status_code=201)
def create_product(body: ProductIn, services: Services = Depends(get_services)):
    return ProductPresenter.render(services.catalog.create(body.model_dump()))


@router.put("/products/{product_id}")
def update_product(product_id: UUID, body: ProductIn, services: Services = Depends(get_services)):
    return ProductPresenter.render(services.catalog.update(product_id, body.model_dump()))
