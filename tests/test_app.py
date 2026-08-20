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


def test_models_endpoint_lists_usable_models(client):
    fake = [{"name": "gemini-3.6-flash", "display_name": "Flash", "input_token_limit": 1048576}]
    with patch.object(web, "list_models", return_value=fake):
        body = client.get("/api/models").json()
    assert body["models"][0]["name"] == "gemini-3.6-flash"
    assert body["default"] == web.DEFAULT_MODEL


def test_models_endpoint_reports_failure_without_crashing(client):
    with patch.object(web, "list_models", side_effect=AgentError("bad key")):
        response = client.get("/api/models")
    assert response.status_code == 502
    assert response.json()["models"] == []


# --- startup robustness -----------------------------------------------------

import socket  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402


def test_port_is_free_detects_a_listener():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        assert web._port_is_free("127.0.0.1", port) is False
    # once closed, the port reads as free again
    assert web._port_is_free("127.0.0.1", port) is True


def test_browser_waits_for_a_slow_server(monkeypatch):
    """Regression: opening on a fixed timer raced the server and showed an error page."""
    opened = []
    monkeypatch.setattr(web.webbrowser, "open", lambda url: opened.append(url))

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    thread = threading.Thread(
        target=web._open_when_ready, args=("127.0.0.1", port, "http://x"), kwargs={"timeout": 5.0}
    )
    thread.start()
    time.sleep(0.8)
    assert opened == [], "browser opened before anything was listening"

    with socket.socket() as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port))
        srv.listen(1)
        thread.join(timeout=5)
        assert opened == ["http://x"]


def test_browser_open_gives_up_rather_than_hanging(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(web.webbrowser, "open", lambda url: opened.append(url))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    web._open_when_ready("127.0.0.1", port, "http://x", timeout=1.0)
    assert opened == []
    assert "did not come up" in capsys.readouterr().out


def test_first_free_port_steps_past_occupied_ones():
    with socket.socket() as a, socket.socket() as b:
        a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        a.bind(("127.0.0.1", 0))
        a.listen(1)
        base = a.getsockname()[1]
        b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            b.bind(("127.0.0.1", base + 1))
            b.listen(1)
        except OSError:
            pass  # neighbour already taken by something else; still fine
        found = web._first_free_port("127.0.0.1", base)
        assert found is not None
        assert found > base


def test_first_free_port_gives_up_on_a_full_span():
    with socket.socket() as a:
        a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        a.bind(("127.0.0.1", 0))
        a.listen(1)
        port = a.getsockname()[1]
        assert web._first_free_port("127.0.0.1", port, span=1) is None
