import json

from youtube_helpers import stage_knowledge


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
