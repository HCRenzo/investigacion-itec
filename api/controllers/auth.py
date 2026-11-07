from fastapi import APIRouter, Depends

from api.container import Services
from api.controllers.deps import current_user, get_services
from api.models import User
from api.views.presenters import UserPresenter
from api.views.schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth")


@router.post("/register", status_code=201)
def register(body: RegisterRequest, services: Services = Depends(get_services)):
    return UserPresenter.session(*services.auth.register(body.name, body.email, body.password))


@router.post("/login")
def login(body: LoginRequest, services: Services = Depends(get_services)):
    return UserPresenter.session(*services.auth.login_customer(body.email, body.password))


@router.get("/me")
def me(user: User = Depends(current_user)):
    return UserPresenter.render(user)
