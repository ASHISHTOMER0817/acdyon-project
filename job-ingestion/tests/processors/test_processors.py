"""Processor unit tests — no network."""

from app.processors.cleaner import ContentCleaner
from app.processors.deduplicator import Deduplicator
from app.processors.normalizer import Normalizer


def test_cleaner_strips_scripts_and_tags():
    raw = "<html><script>alert(1)</script><body>Python Engineer at Globex</body></html>"
    text = ContentCleaner().clean(raw)
    assert "alert" not in text
    assert "Python Engineer" in text


def test_cleaner_preserves_json():
    raw = '{"title": "Dev", "company": "Acme"}'
    assert ContentCleaner().clean(raw).startswith("{")


def test_job_id_stable_for_same_url():
    d = Deduplicator()
    a = d.job_id("remoteok", "https://remoteok.com/l/1?utm_source=x")
    b = d.job_id("remoteok", "https://remoteok.com/l/1")
    assert a == b


def test_drop_known_counts_duplicates():
    d = Deduplicator()
    obj = {"title": "Dev", "company": "Acme", "source_url": "https://ex.com/j/1"}
    job_id = d.job_id("ex", "https://ex.com/j/1", "Dev", "Acme", "")
    fresh, dupes = d.drop_known([obj], {job_id}, "ex")
    assert dupes == 1
    assert fresh == []


def test_normalizer_preserves_gemini_object():
    gemini = {
        "title": "Dev",
        "company": "Acme",
        "source_url": "https://ex.com/j/1",
        "location": "Remote",
    }
    job = Normalizer().to_job(gemini, source_name="ex", page_url="https://ex.com/j/1")
    assert job.gemini_object["title"] == "Dev"
    assert "_memory_id" not in job.gemini_object
    assert job.as_display_dict()["_memory_id"] == job.id
