from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

DEFAULT_SETTINGS_PATH = Path("settings.json")


@dataclass
class SchedulerConfig:
    enabled: bool = False
    time_utc: Optional[str] = None  # format HH:MM


@dataclass
class Settings:
    channels: List[str] = field(default_factory=list)
    allow_user_ids: List[int] = field(default_factory=list)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    def add_channels(self, new_channels: List[str]) -> None:
        existing = set(self.channels)
        for ch in new_channels:
            if ch not in existing:
                self.channels.append(ch)
                existing.add(ch)

    def remove_channels(self, remove: List[str]) -> None:
        remove_set = set(remove)
        self.channels = [ch for ch in self.channels if ch not in remove_set]


def load_settings(path: Path = DEFAULT_SETTINGS_PATH, env_channels: Optional[List[str]] = None) -> Settings:
    if not path.exists():
        settings = Settings()
        if env_channels:
            settings.channels = env_channels
        return settings
    raw = json.loads(path.read_text())
    scheduler_raw = raw.get("scheduler", {}) if isinstance(raw, dict) else {}
    scheduler = SchedulerConfig(
        enabled=bool(scheduler_raw.get("enabled", False)),
        time_utc=scheduler_raw.get("time_utc"),
    )
    settings = Settings(
        channels=raw.get("channels", []) if isinstance(raw, dict) else [],
        allow_user_ids=raw.get("allow_user_ids", []) if isinstance(raw, dict) else [],
        scheduler=scheduler,
    )
    if env_channels:
        settings.add_channels(env_channels)
    return settings


def save_settings(path: Path, settings: Settings) -> None:
    payload = {
        "channels": settings.channels,
        "allow_user_ids": settings.allow_user_ids,
        "scheduler": {
            "enabled": settings.scheduler.enabled,
            "time_utc": settings.scheduler.time_utc,
        },
    }
    path.write_text(json.dumps(payload, indent=2))
