from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.analyses.router import router as analyses_router
from app.modules.health.router import router as health_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.auth.router import router as auth_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    application = FastAPI(title=config.app_name, version="0.1.0")
    if settings is not None:
        application.dependency_overrides[get_settings] = lambda: config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    @application.middleware("http")
    async def private_cache_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(analyses_router)
    application.include_router(dashboard_router)
    return application


app = create_app()
