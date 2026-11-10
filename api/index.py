"""Application entry point (Vercel looks for `app` here)."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Make `import api...` work regardless of the host's working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.controllers import admin, auth, pages, research, shop
from api.controllers.pages import STATIC
from api.database import ensure_initialized
from api.errors import DomainError


class NoCacheStaticFiles(StaticFiles):
    """Browsers must revalidate the JS/CSS on every load so UI changes show up immediately."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_initialized()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Tienda y modulo de ventas", version="3.0.0", lifespan=lifespan)

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    for router in (pages.router, auth.router, shop.router, admin.public, admin.router, research.router):
        app.include_router(router)
    if STATIC.is_dir():
        app.mount("/static", NoCacheStaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
