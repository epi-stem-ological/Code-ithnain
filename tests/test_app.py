"""Tests for the local web UI's API."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app as web
from agent import AgentError, Analysis, Highlight, InsightCategory, Takeaway
from extractor import ExtractionError, VideoData

VIDEO = VideoData(
    video_id="6lnGZmAf61A", url="https://www.youtube.com/watch?v=6lnGZmAf61A",
    title="T", author="A", description="d", duration_seconds=125,
    transcript="[00:00:00] hi", transcript_language="en", segment_count=1,
)
NO_CAPTIONS = VideoData(
    video_id="x", url="u", title="T", author="A", description="d",
    transcript=None, transcript_error="no transcript: the uploader has disabled captions",
)
ANALYSIS = Analysis(
    summary="s",
    takeaways=[Takeaway(takeaway="t", why="w")],
    highlights=[Highlight(timestamp="00:00:30", title="h", detail="d")],
    insights=[InsightCategory(category="C", points=["p"])],
)


@pytest.fixture
def client():
    web.app.state.demo = False
    return TestClient(web.app)


def test_index_serves_the_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "YouTube Agent Engine" in response.text


def test_status_reports_key_presence(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert client.get("/api/status").json()["has_key"] is False
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert client.get("/api/status").json()["has_key"] is True


def test_analyze_happy_path(client):
    with patch.object(web, "extract", return_value=VIDEO), \
         patch.object(web, "analyze", return_value=ANALYSIS):
        response = client.post("/api/analyze", json={"url": "https://youtu.be/6lnGZmAf61A"})

    assert response.status_code == 200
    body = response.json()
    assert body["video"]["video_id"] == "6lnGZmAf61A"
    assert body["analysis"]["takeaways"][0]["takeaway"] == "t"


def test_bad_url_returns_400_with_stage(client):
    with patch.object(web, "extract", side_effect=ExtractionError("not a YouTube URL")):
        response = client.post("/api/analyze", json={"url": "https://vimeo.com/1"})
    assert response.status_code == 400
    assert response.json()["stage"] == "extract"


def test_missing_captions_returns_422_with_reason(client):
    with patch.object(web, "extract", return_value=NO_CAPTIONS):
        response = client.post("/api/analyze", json={"url": "https://youtu.be/x"})
    assert response.status_code == 422
    body = response.json()
    assert body["stage"] == "transcript"
    assert "disabled captions" in body["error"]


def test_agent_failure_returns_502(client):
    with patch.object(web, "extract", return_value=VIDEO), \
         patch.object(web, "analyze", side_effect=AgentError("bad key")):
        response = client.post("/api/analyze", json={"url": "https://youtu.be/x"})
    assert response.status_code == 502
    assert response.json()["stage"] == "analyze"


def test_options_are_forwarded(client):
    with patch.object(web, "extract", return_value=VIDEO) as ex, \
         patch.object(web, "analyze", return_value=ANALYSIS) as an:
        client.post("/api/analyze", json={
            "url": "https://youtu.be/x", "task": "list books",
            "model": "gemini-2.5-pro", "languages": ["es", "en"],
        })
    assert ex.call_args.kwargs["languages"] == ["es", "en"]
    assert an.call_args.kwargs["task"] == "list books"
    assert an.call_args.kwargs["model"] == "gemini-2.5-pro"


def test_demo_mode_needs_no_network_or_key(client):
    web.app.state.demo = True
    response = client.post("/api/analyze", json={"url": "anything"})
    body = response.json()
    assert response.status_code == 200
    assert body["demo"] is True
    assert body["analysis"]["takeaways"]


def test_demo_summary_contains_no_markdown_syntax(client):
    web.app.state.demo = True
    summary = client.post("/api/analyze", json={"url": "x"}).json()["analysis"]["summary"]
    for token in ("**", "`", "__"):
        assert token not in summary


def test_oversized_url_is_rejected(client):
    response = client.post("/api/analyze", json={"url": "x" * 3000})
    assert response.status_code == 422  # pydantic validation
