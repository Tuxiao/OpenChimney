from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from .models import AppSetting

HERMES_SETTING_KEY = "runner.hermes.config"

DEFAULT_HERMES_CONFIG: dict[str, Any] = {
    "enabled": True,
    "model": "anthropic/claude-sonnet-4.6",
    "provider": None,
    "base_url": None,
    "api_key": None,
    "task_root": "/runner/workspaces",
    "hermes_home": "/runner/.hermes",
    "max_iterations": 20,
    "default_toolsets": ["safe"],
    "allowed_toolsets": ["safe", "web", "search", "vision", "image_gen", "mcp-sqlite-service"],
    "memory_mode": "tenant",
    "timeout_seconds": 300,
}


def default_hermes_config() -> dict[str, Any]:
    return {
        **DEFAULT_HERMES_CONFIG,
        "default_toolsets": list(DEFAULT_HERMES_CONFIG["default_toolsets"]),
        "allowed_toolsets": list(DEFAULT_HERMES_CONFIG["allowed_toolsets"]),
    }


def merged_hermes_config(value: Optional[dict[str, Any]]) -> dict[str, Any]:
    config = default_hermes_config()
    if isinstance(value, dict):
        config.update({key: value for key, value in value.items() if key in config})
    config["default_toolsets"] = _list_value(config.get("default_toolsets"))
    config["allowed_toolsets"] = _list_value(config.get("allowed_toolsets"))
    config["provider"] = _optional_str(config.get("provider"))
    config["base_url"] = _optional_str(config.get("base_url"))
    config["api_key"] = _optional_str(config.get("api_key"))
    return config


def load_hermes_setting(db: Session) -> tuple[dict[str, Any], AppSetting | None]:
    setting = db.query(AppSetting).filter(AppSetting.key == HERMES_SETTING_KEY).one_or_none()
    return merged_hermes_config(setting.value_json if setting else None), setting


def ensure_hermes_setting(db: Session) -> AppSetting:
    config, setting = load_hermes_setting(db)
    if setting is None:
        setting = AppSetting(key=HERMES_SETTING_KEY, value_json=config, is_secret=True)
        db.add(setting)
        db.flush()
    return setting


def public_hermes_config(config: dict[str, Any], updated_at: datetime | None = None) -> dict[str, Any]:
    return {
        "enabled": bool(config.get("enabled", True)),
        "model": str(config.get("model") or DEFAULT_HERMES_CONFIG["model"]),
        "provider": _optional_str(config.get("provider")),
        "base_url": _optional_str(config.get("base_url")),
        "api_key_configured": bool(_optional_str(config.get("api_key"))),
        "task_root": str(config.get("task_root") or DEFAULT_HERMES_CONFIG["task_root"]),
        "hermes_home": str(config.get("hermes_home") or DEFAULT_HERMES_CONFIG["hermes_home"]),
        "max_iterations": int(config.get("max_iterations") or DEFAULT_HERMES_CONFIG["max_iterations"]),
        "default_toolsets": _list_value(config.get("default_toolsets")),
        "allowed_toolsets": _list_value(config.get("allowed_toolsets")),
        "memory_mode": str(config.get("memory_mode") or DEFAULT_HERMES_CONFIG["memory_mode"]),
        "timeout_seconds": float(config.get("timeout_seconds") or DEFAULT_HERMES_CONFIG["timeout_seconds"]),
        "updated_at": updated_at,
    }


def runner_hermes_config(config: dict[str, Any], updated_at: datetime | None = None) -> dict[str, Any]:
    payload = public_hermes_config(config, updated_at)
    payload["api_key"] = _optional_str(config.get("api_key"))
    return payload


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []
