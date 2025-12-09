from job_finder import digest
from job_finder.models import VacancyNormalized
from job_finder.resources import messages


def _sample_vacancy(**kwargs):
    base = dict(
        id=1,
        is_relevant=True,
        relevance_reason="relevant",
        title="Senior PM",
        company="Acme",
        level="senior",
        role="Product Manager",
        location="Remote",
        remote_type="remote",
        salary_min_usd=100000,
        salary_max_usd=120000,
        salary_raw=None,
        language="en",
        source_channel="@a",
        source_message_id=10,
        source_link="https://t.me/a/10",
        raw_snippet="Desc",
    )
    base.update(kwargs)
    return VacancyNormalized(**base)


def test_empty_digest() -> None:
    assert digest.build_digest([]) == messages.EMPTY_DIGEST


def test_digest_sorts_remote_first() -> None:
    remote = _sample_vacancy(id=1, location="Remote", remote_type="remote", salary_max_usd=120000)
    barcelona = _sample_vacancy(
        id=2,
        location="Barcelona office",
        remote_type="onsite",
        salary_max_usd=130000,
    )
    onsite = _sample_vacancy(id=3, location="Berlin", remote_type="onsite", salary_max_usd=150000)
    result = digest.build_digest([onsite, barcelona, remote])
    lines = result.splitlines()
    first_block = "\n".join(lines[4:9])
    assert "1)" in lines[4]
    assert "Remote" in first_block
