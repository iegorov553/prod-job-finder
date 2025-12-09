from datetime import datetime, timezone
from types import SimpleNamespace

from job_finder import scraper
from job_finder.models import RawPost


def test_extract_links() -> None:
    text = "Check https://a.com and http://b.com"
    assert scraper._extract_links(text) == ["https://a.com", "http://b.com"]


def test_message_to_raw_post_converts_date() -> None:
    message = SimpleNamespace(
        id=10,
        message="text https://a.com",
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    raw = scraper._message_to_raw_post("@channel", message)
    assert raw.id == 10
    assert raw.source_link.endswith("/10")
    assert "https://a.com" in raw.links


def test_get_max_message_id() -> None:
    posts = [
        RawPost(id=1, channel="@a", date="", text="", links=[], source_link=None),
        RawPost(id=3, channel="@a", date="", text="", links=[], source_link=None),
    ]
    assert scraper.get_max_message_id(posts, "@a") == 3
