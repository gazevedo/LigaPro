import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.config.settings import get_settings
from app.controllers import health, settings
from app.core.logging import configure_logging
from app.database.mongo import create_client

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_settings()
    client = create_client(config)
    app.state.database = client[config.mongodb_database_name]
    try:
        app.state.database.command("ping")
        app.state.database["app_settings"].create_index("key", unique=True)
        logger.info("MongoDB connected; app_settings index ready")
        yield
    finally:
        client.close()


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(title="LigaPro API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=config.cors_origins,
        allow_methods=["GET", "PUT"], allow_headers=["Content-Type"],
    )

    @app.exception_handler(PyMongoError)
    async def database_error(request: Request, exc: PyMongoError):
        logger.error("Database operation failed (%s)", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Unhandled application error (%s)", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    return app


app = create_app()
