from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ChannelState:
    username: str
    last_message_id: Optional[int] = None


@dataclass
class State:
    channels: List[ChannelState] = field(default_factory=list)

    def get_last_message_id(self, channel: str) -> Optional[int]:
        for item in self.channels:
            if item.username == channel:
                return item.last_message_id
        return None

    def update_last_message_id(self, channel: str, last_id: int) -> None:
        for item in self.channels:
            if item.username == channel:
                item.last_message_id = last_id
                return
        self.channels.append(ChannelState(username=channel, last_message_id=last_id))


def _ensure_channels(state: State, channels: List[str]) -> State:
    known = {channel.username for channel in state.channels}
    for channel_name in channels:
        if channel_name not in known:
            state.channels.append(ChannelState(username=channel_name, last_message_id=None))
    return state


def load_state(path: Path, channels: List[str]) -> State:
    if not path.exists():
        return _ensure_channels(State(), channels)
    raw = json.loads(path.read_text())
    channel_states: List[ChannelState] = []
    for channel_obj in raw.get("channels", []):
        username = channel_obj.get("username")
        if not username:
            continue
        last_message_id = channel_obj.get("last_message_id")
        channel_states.append(ChannelState(username=username, last_message_id=last_message_id))
    return _ensure_channels(State(channels=channel_states), channels)


def save_state(path: Path, state: State) -> None:
    payload: Dict[str, List[Dict[str, Optional[int]]]] = {
        "channels": [
            {
                "username": channel.username,
                "last_message_id": channel.last_message_id,
            }
            for channel in state.channels
        ]
    }
    path.write_text(json.dumps(payload, indent=2))
