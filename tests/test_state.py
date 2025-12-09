from pathlib import Path

from job_finder import state


def test_load_state_creates_defaults(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    loaded = state.load_state(path, ["@a", "@b"])
    assert loaded.get_last_message_id("@a") is None
    assert loaded.get_last_message_id("@b") is None


def test_state_save_and_update(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    current = state.load_state(path, ["@a"])
    current.update_last_message_id("@a", 42)
    state.save_state(path, current)

    reloaded = state.load_state(path, ["@a"])
    assert reloaded.get_last_message_id("@a") == 42
