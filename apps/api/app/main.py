from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import AppConfig
from .db import create_db_engine, create_session_factory
from .migrations import init_schema, seed_data
from .routers import admin, auth, conversations, members, orders, runner, tasks


def create_app(config: Optional[AppConfig] = None) -> FastAPI:
    app_config = config or AppConfig.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app_config.create_schema_on_startup:
            init_schema(app.state.engine)
        if app_config.seed_on_startup:
            with app.state.SessionLocal() as db:
                seed_data(db, app_config)
        yield

    app = FastAPI(title="OpenChimney API", version="0.1.0", lifespan=lifespan)
    app.state.config = app_config
    app.state.engine = create_db_engine(app_config.database_url)
    app.state.SessionLocal = create_session_factory(app.state.engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_config.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        with app.state.engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return {"status": "ok", "database": "ok"}

    app.include_router(auth.router)
    app.include_router(members.router)
    app.include_router(orders.router)
    app.include_router(tasks.router)
    app.include_router(conversations.router)
    app.include_router(admin.router)
    app.include_router(runner.router)
    return app


app = create_app()
