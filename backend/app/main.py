from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.users.router import router as users_router


def create_app() -> FastAPI:
    application = FastAPI(title=get_settings().app_name)
    application.include_router(users_router)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Process liveness only; this does not check database readiness."""
        return {"status": "ok"}

    return application
