import json

from youtube_helpers import finalize_reasoning, list_claims, stage_knowledge, timestamp_link


def test_stage_knowledge_creates_file(tmp_path):
    path = tmp_path / "topic.json"
    video = {
        "video": {"title": "Video 1", "url": "https://youtube.com/watch?v=v1"},
        "claims": [{"statement": "Claim A", "stated_as": "explicit", "timestamp": "00:10"}],
        "definitions": [{"term": "X", "explanation": "Y"}],
        "examples": ["Example A"],
    }
    stage_knowledge(str(path), "some topic", json.dumps(video))

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["topic"] == "some topic"
    assert [c["statement"] for c in data["claims"]] == ["Claim A"]
    assert data["claims"][0]["corroborated_by"] == ["https://youtube.com/watch?v=v1"]
    assert data["definitions"] == [{"term": "X", "explanation": "Y"}]
    assert data["examples"] == ["Example A"]
    assert data["videos"] == [{"title": "Video 1", "url": "https://youtube.com/watch?v=v1"}]


def test_stage_knowledge_corroborates_restated_claim_instead_of_duplicating(tmp_path):
    path = tmp_path / "topic.json"
    video1 = {
        "video": {"title": "Video 1", "url": "https://youtube.com/watch?v=v1"},
        "claims": [{"statement": "Shared claim", "stated_as": "explicit", "timestamp": "00:10"}],
    }
    video2 = {
        "video": {"title": "Video 2", "url": "https://youtube.com/watch?v=v2"},
        "claims": [{"statement": "shared claim", "stated_as": "explicit", "timestamp": "01:20"}],
    }
    stage_knowledge(str(path), "some topic", json.dumps(video1))
    stage_knowledge(str(path), "some topic", json.dumps(video2))

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["claims"]) == 1
    claim = data["claims"][0]
    assert claim["corroborated_by"] == ["https://youtube.com/watch?v=v1", "https://youtube.com/watch?v=v2"]
    assert len(claim["timestamps"]) == 2


def test_stage_knowledge_does_not_duplicate_same_source_twice(tmp_path):
    path = tmp_path / "topic.json"
    video = {
        "video": {"title": "Video 1", "url": "https://youtube.com/watch?v=v1"},
        "claims": [
            {"statement": "Claim A", "stated_as": "explicit", "timestamp": "00:10"},
            {"statement": "Claim A", "stated_as": "explicit", "timestamp": "00:20"},
        ],
    }
    stage_knowledge(str(path), "some topic", json.dumps(video))

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["claims"]) == 1
    assert data["claims"][0]["corroborated_by"] == ["https://youtube.com/watch?v=v1"]
    assert len(data["claims"][0]["timestamps"]) == 2


def test_restated_claim_matches_despite_punctuation_and_case(tmp_path):
    path = tmp_path / "topic.json"
    for n, statement in enumerate(["Caching cuts latency.", "caching cuts latency"], start=1):
        video = {
            "video": {"title": f"Video {n}", "url": f"https://youtube.com/watch?v=v{n}"},
            "claims": [{"statement": statement, "timestamp": "00:10"}],
        }
        status = stage_knowledge(str(path), "some topic", json.dumps(video))

    assert status["claim_count"] == 1
    assert status["corroborated_claims"] == 1
    assert list_claims(str(path)) == ["Caching cuts latency."]


def test_timestamps_get_a_link_that_opens_the_video_at_that_moment(tmp_path):
    assert timestamp_link("https://youtube.com/watch?v=v1", "12:34") == "https://youtube.com/watch?v=v1&t=754s"
    assert timestamp_link("https://youtube.com/watch?v=v1", "1:02:03") == "https://youtube.com/watch?v=v1&t=3723s"
    assert timestamp_link("https://youtube.com/watch?v=v1", "around the middle") == "https://youtube.com/watch?v=v1"

    path = tmp_path / "topic.json"
    video = {
        "video": {"title": "Video 1", "url": "https://youtube.com/watch?v=v1"},
        "claims": [{"statement": "Claim A", "timestamp": "02:05"}],
    }
    stage_knowledge(str(path), "some topic", json.dumps(video))

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["claims"][0]["timestamps"][0]["link"] == "https://youtube.com/watch?v=v1&t=125s"


def test_finalize_nests_observations_and_keeps_open_questions(tmp_path):
    path = tmp_path / "nested" / "topic.json"  # parent folder doesn't exist yet, like a fresh clone
    video = {
        "video": {"title": "Video 1", "url": "https://youtube.com/watch?v=v1"},
        "claims": [{"statement": "Claim A", "timestamp": "00:10"}],
        "open_questions": ["What about B?"],
    }
    stage_knowledge(str(path), "some topic", json.dumps(video))
    finalize_reasoning(str(path), json.dumps({"agreements": ["Claim A"]}))
    finalize_reasoning(str(path), json.dumps({"agreements": ["Claim A, revised"]}))  # safe to repeat

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["observations"]["open_questions"] == ["What about B?"]
    assert data["observations"]["claims"][0]["statement"] == "Claim A"
    assert data["reasoning"]["agreements"] == ["Claim A, revised"]
    assert data["reasoning"]["disagreements"] == []  # missing keys come back as empty lists
    assert list_claims(str(path)) == ["Claim A"]
