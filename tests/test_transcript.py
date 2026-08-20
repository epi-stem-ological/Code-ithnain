from youtube_agent.transcript import Segment, Transcript


def make(*pairs):
    return Transcript(
        video_id="dQw4w9WgXcQ",
        language="en",
        segments=[Segment(text=text, start=start, duration=2.0) for text, start in pairs],
    )


def test_text_joins_and_strips():
    assert make(("hello ", 0.0), ("  world", 2.0), ("   ", 4.0)).text == "hello world"


def test_word_count():
    assert make(("one two three", 0.0), ("four", 5.0)).word_count() == 4


def test_timestamp_formatting():
    assert Segment("x", 0.0, 1.0).timestamp == "0:00"
    assert Segment("x", 95.0, 1.0).timestamp == "1:35"
    assert Segment("x", 3725.0, 1.0).timestamp == "1:02:05"


def test_timestamped_text_marks_at_most_every_n_seconds():
    lines = make(("a", 0.0), ("b", 10.0), ("c", 35.0), ("d", 40.0)).timestamped_text(every_seconds=30).splitlines()
    assert lines == ["[0:00] a", "b", "[0:35] c", "d"]
