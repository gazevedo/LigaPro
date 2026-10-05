import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.config.settings import get_settings
from app.controllers import auth, game, health, settings
from app.core.logging import configure_logging
from app.database.mongo import create_client
from app.repositories.game import GameRepository
from app.services.game import process_due

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
        app.state.database["users"].create_index("email", unique=True)
        app.state.database["users"].create_index(
            "google_id", unique=True, partialFilterExpression={"google_id": {"$type": "string"}}
        )
        app.state.database["user_sessions"].create_index("refresh_token_hash", unique=True)
        app.state.database["user_sessions"].create_index("user_id")
        app.state.database["user_sessions"].create_index("expires_at", expireAfterSeconds=0)
        app.state.database["auth_rate_limits"].create_index("expires_at", expireAfterSeconds=0)
        repository = GameRepository(app.state.database)
        repository.initialize()

        async def maintenance():
            while True:
                try:
                    await asyncio.to_thread(process_due, repository)
                except Exception as exc:
                    logger.error("Game maintenance failed (%s)", type(exc).__name__)
                await asyncio.sleep(30)

        task = asyncio.create_task(maintenance())
        logger.info("MongoDB connected; application indexes ready")
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        client.close()


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(title="LigaPro API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "PUT", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(PyMongoError)
    async def database_error(request: Request, exc: PyMongoError):
        logger.error("Database operation failed (%s)", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Unhandled application error (%s)", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(game.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    return app


app = create_app()
