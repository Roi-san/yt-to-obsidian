import vault_helpers


def test_slugify():
    assert vault_helpers.slugify("How DNS Resolution Works!") == "how-dns-resolution-works"
    assert vault_helpers.slugify("  leading/trailing --- junk  ") == "leading-trailing-junk"


def test_write_note_then_list_notes_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_helpers, "_vault_path", lambda: tmp_path)

    result = vault_helpers.write_note(
        "My Test Note",
        ["https://youtube.com/watch?v=v1"],
        "Body text.",
        tags=["tag-a", "tag-b"],
    )

    notes = vault_helpers.list_notes()
    assert len(notes) == 1
    assert notes[0]["slug"] == result["slug"]
    assert notes[0]["title"] == "My Test Note"
    assert notes[0]["tags"] == ["tag-a", "tag-b"]


def test_add_backlink_creates_related_section_once(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_helpers, "_vault_path", lambda: tmp_path)
    note_path = tmp_path / "existing-note.md"
    note_path.write_text("---\ntitle: Existing\n---\n\nSome body.\n", encoding="utf-8")

    vault_helpers.add_backlink("existing-note", "new-note")
    vault_helpers.add_backlink("existing-note", "new-note")

    text = note_path.read_text(encoding="utf-8")
    assert text.count("[[new-note]]") == 1


def test_title_with_colon_round_trips_and_same_title_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_helpers, "_vault_path", lambda: tmp_path)

    first = vault_helpers.write_note("HTTP/2: How \"Streams\" Work", [], "First body.", tags=["Web Perf"])
    second = vault_helpers.write_note("HTTP/2: How \"Streams\" Work", [], "Second body.")

    assert first["slug"] != second["slug"]
    assert "First body." in (tmp_path / f"{first['slug']}.md").read_text(encoding="utf-8")
    notes = {n["slug"]: n for n in vault_helpers.list_notes()}
    assert notes[first["slug"]]["title"] == "HTTP/2: How \"Streams\" Work"
    assert notes[first["slug"]]["tags"] == ["web-perf"]


def test_list_notes_still_reads_old_unquoted_titles(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_helpers, "_vault_path", lambda: tmp_path)
    (tmp_path / "old-note.md").write_text("---\ntitle: Old Plain Title\ntags: [a, b]\n---\n\nBody.\n", encoding="utf-8")

    assert vault_helpers.list_notes() == [{"slug": "old-note", "title": "Old Plain Title", "tags": ["a", "b"]}]
