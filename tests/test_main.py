import base64

import main as main_module


def test_ensure_session_file(tmp_path) -> None:
    session_bytes = b"dummy"
    encoded = base64.b64encode(session_bytes).decode()
    session_name = "telegram_session"
    # run helper
    main_module._ensure_session_file(session_name, encoded, None, tmp_path)
    session_path = tmp_path / f"{session_name}.session"
    assert session_path.exists()
    assert session_path.read_bytes() == session_bytes


def test_ensure_session_file_with_string_session(tmp_path) -> None:
    """String session should skip file creation."""
    session_name = "telegram_session"
    # With string_session, no file should be created
    main_module._ensure_session_file(session_name, None, "string_session_value", tmp_path)
    session_path = tmp_path / f"{session_name}.session"
    assert not session_path.exists()


def test_ensure_session_file_already_exists(tmp_path) -> None:
    """Existing session file should not be overwritten."""
    session_name = "telegram_session"
    session_path = tmp_path / f"{session_name}.session"
    original_content = b"original"
    session_path.write_bytes(original_content)

    new_encoded = base64.b64encode(b"new_content").decode()
    main_module._ensure_session_file(session_name, new_encoded, None, tmp_path)

    # Original content should be preserved
    assert session_path.read_bytes() == original_content
