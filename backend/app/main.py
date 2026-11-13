from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.projects.router import router as projects_router
from app.modules.users.router import router as users_router


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "PATCH"],
            allow_headers=["Authorization", "Content-Type"],
        )
    application.include_router(users_router)
    application.include_router(projects_router)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Process liveness only; this does not check database readiness."""
        return {"status": "ok"}

    return application
