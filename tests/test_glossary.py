from translation_core.glossary import (
    GlossaryEntry,
    find_relevant_entries,
    load_glossary,
    save_glossary,
)


def test_load_glossary_on_missing_file_returns_empty_list(tmp_path):
    assert load_glossary(tmp_path / "glossary.json") == []


def test_save_then_load_round_trips_entries(tmp_path):
    path = tmp_path / "glossary.json"
    entries = [
        GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch3"),
        GlossaryEntry(term="李明", translation="Lý Minh", note="", chapter_id="ch1"),
    ]

    save_glossary(path, entries)
    loaded = load_glossary(path)

    assert loaded == entries


def test_find_relevant_entries_matches_literal_substring():
    entries = [
        GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch3"),
        GlossaryEntry(term="李明", translation="Lý Minh", note="", chapter_id="ch1"),
    ]

    result = find_relevant_entries(entries, "龙王今天很生气，李明害怕地跑开了。")

    assert result == entries


def test_find_relevant_entries_excludes_non_matching_terms():
    entries = [GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch3")]

    result = find_relevant_entries(entries, "今天天气很好。")

    assert result == []
