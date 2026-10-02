from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.analyses.router import router as analyses_router
from app.modules.health.router import router as health_router
from app.modules.dashboard.router import router as dashboard_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    application = FastAPI(title=config.app_name, version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Demo-Workspace-ID"],
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(analyses_router)
    application.include_router(dashboard_router)
    return application


app = create_app()
