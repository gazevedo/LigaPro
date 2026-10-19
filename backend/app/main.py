import asyncio
import logging
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.background import BackgroundTasks

from app.config.settings import get_settings
from app.controllers import auth, game, health, live, push, settings
from app.core.logging import configure_logging
from app.database.mongo import create_client
from app.repositories.game import GameRepository
from app.services.competition import CompetitionService
from app.services.game import process_due
from app.services.monthly_finance import bootstrap_economy
from app.services.player_contracts import ContractService
from app.services.player_development import bootstrap_player_attributes
from app.services.push_notifications import send_match_reminders

configure_logging()
logger = logging.getLogger(__name__)


async def run_game_maintenance(manager, repository, config):
    for name, operation in (
        ("live", manager.start_due),
        ("scheduled", lambda: asyncio.to_thread(process_due, repository)),
        ("reminders", lambda: asyncio.to_thread(send_match_reminders, repository, config)),
    ):
        try:
            await operation()
        except Exception:
            logger.exception("Game maintenance stage failed: %s", name)


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
            "name_key", unique=True, partialFilterExpression={"name_key": {"$type": "string"}}
        )
        app.state.database["users"].create_index(
            "google_id", unique=True, partialFilterExpression={"google_id": {"$type": "string"}}
        )
        app.state.database["user_sessions"].create_index("refresh_token_hash", unique=True)
        app.state.database["user_sessions"].create_index("user_id")
        app.state.database["user_sessions"].create_index("expires_at", expireAfterSeconds=0)
        app.state.database["auth_rate_limits"].create_index("expires_at", expireAfterSeconds=0)
        app.state.database.push_subscriptions.create_index("user_id")
        app.state.database.push_deliveries.create_index("expires_at", expireAfterSeconds=0)
        repository = GameRepository(app.state.database)
        repository.initialize()
        CompetitionService(repository).bootstrap()
        ContractService(repository).bootstrap()
        bootstrap_player_attributes(repository)
        bootstrap_economy(repository)

        from app.services.live_match import MatchRoomManager

        app.state.match_rooms = MatchRoomManager(repository)
        await app.state.match_rooms.recover()

        tick_lock = asyncio.Lock()
        last_attempt = float("-inf")

        async def tick():
            nonlocal last_attempt
            async with tick_lock:
                if monotonic() - last_attempt < 30:
                    return
                last_attempt = monotonic()
                await run_game_maintenance(app.state.match_rooms, repository, config)

        app.state.request_game_tick = tick

        async def maintenance():
            while True:
                await tick()
                await asyncio.sleep(30)

        task = asyncio.create_task(maintenance())
        logger.info("MongoDB connected; application indexes ready")
        try:
            yield
        finally:
            app.state.request_game_tick = lambda: None
            await app.state.match_rooms.close()
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

    @app.middleware("http")
    async def refresh_due_games(request: Request, call_next):
        response = await call_next(request)
        if request.url.path in {
            "/api/calendar",
            "/api/matches/upcoming",
            "/api/game/status",
        }:
            kick = getattr(app.state, "request_game_tick", None)
            if kick:
                # Send the screen data first, then await maintenance as part of
                # the response lifecycle instead of detaching a cancellable task.
                background = BackgroundTasks()
                if response.background:
                    background.add_task(response.background)
                background.add_task(kick)
                response.background = background
        return response

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

    app.include_router(live.router)
    app.include_router(game.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(push.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    return app


app = create_app()
