from datetime import datetime, timezone
from types import SimpleNamespace

from job_finder import scraper
from job_finder.models import RawPost


def test_extract_links() -> None:
    message = SimpleNamespace(
        message="Check https://a.com and http://b.com",
        entities=[],
        reply_markup=None,
    )
    assert scraper._extract_links(message) == ["https://a.com", "http://b.com"]


def test_extract_links_from_entities_and_buttons() -> None:
    message = SimpleNamespace(
        message="Linked post",
        entities=[SimpleNamespace(url="https://linkedin.com/jobs/view/123")],
        reply_markup=SimpleNamespace(
            buttons=[[SimpleNamespace(url="https://company.com/careers/pm")]]
        ),
    )
    assert scraper._extract_links(message) == [
        "https://linkedin.com/jobs/view/123",
        "https://company.com/careers/pm",
    ]


def test_extract_links_normalizes_and_deduplicates() -> None:
    message = SimpleNamespace(
        message="Go https://a.com, and https://a.com!",
        entities=[],
        reply_markup=None,
    )
    assert scraper._extract_links(message) == ["https://a.com"]


def test_message_to_raw_post_converts_date() -> None:
    message = SimpleNamespace(
        id=10,
        message="text https://a.com",
        entities=[],
        reply_markup=None,
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    raw = scraper._message_to_raw_post("@channel", message)
    assert raw.id == 10
    assert raw.source_link is not None
    assert raw.source_link.endswith("/10")
    assert "https://a.com" in raw.links


def test_get_max_message_id() -> None:
    posts = [
        RawPost(id=1, channel="@a", date="", text="", links=[], source_link=None),
        RawPost(id=3, channel="@a", date="", text="", links=[], source_link=None),
    ]
    assert scraper.get_max_message_id(posts, "@a") == 3
