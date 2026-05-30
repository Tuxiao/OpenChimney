from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    database_url: str = "sqlite:///./data/api.sqlite3"
    runner_key: str = "dev-runner-key"
    cors_origins: tuple[str, ...] = ("*",)
    session_ttl_seconds: int = 60 * 60 * 24 * 30
    create_schema_on_startup: bool = True
    seed_on_startup: bool = True
    default_admin_email: str = "admin@example.com"
    default_admin_password: str = "admin1234"

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            runner_key=os.getenv("RUNNER_KEY", os.getenv("RUNNER_API_KEY", cls.runner_key)),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv("CORS_ORIGINS", "*").split(",")
                if origin.strip()
            )
            or cls.cors_origins,
            session_ttl_seconds=int(
                os.getenv("SESSION_TTL_SECONDS", str(cls.session_ttl_seconds))
            ),
            create_schema_on_startup=os.getenv("CREATE_SCHEMA_ON_STARTUP", "1") != "0",
            seed_on_startup=os.getenv("SEED_ON_STARTUP", "1") != "0",
            default_admin_email=os.getenv("DEFAULT_ADMIN_EMAIL", cls.default_admin_email),
            default_admin_password=os.getenv(
                "DEFAULT_ADMIN_PASSWORD", cls.default_admin_password
            ),
        )
