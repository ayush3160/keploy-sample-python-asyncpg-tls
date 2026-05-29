import logging

from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.errors import HttpError, http_error_handler, integrity_error_handler
from app.routers import health, nda_command, project_provider, project_provider_batch, project_provider_command

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.name)

    app.add_exception_handler(HttpError, http_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)

    app.include_router(health.router)
    app.include_router(project_provider.router)
    app.include_router(project_provider_batch.router)
    app.include_router(project_provider_command.router)
    app.include_router(nda_command.router)

    return app


app = create_app()
