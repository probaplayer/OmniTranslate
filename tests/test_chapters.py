import time

from translation_core.chapters import (
    ChapterRecord,
    get_recent,
    load_chapters,
    record_chapter,
    save_chapters,
)


def test_load_chapters_on_missing_file_returns_empty_list(tmp_path):
    assert load_chapters(tmp_path / "chapters.json") == []


def test_record_chapter_appends_new_chapter(tmp_path):
    path = tmp_path / "chapters.json"

    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1-vi.txt")

    records = load_chapters(path)
    assert len(records) == 1
    assert records[0].chapter_id == "ch1"
    assert records[0].source_path == "src/ch1.txt"
    assert records[0].output_path == "out/ch1-vi.txt"


def test_record_chapter_updates_existing_chapter_instead_of_duplicating(tmp_path):
    path = tmp_path / "chapters.json"

    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1-vi.txt")
    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1-vi-fixed.txt")

    records = load_chapters(path)
    assert len(records) == 1
    assert records[0].output_path == "out/ch1-vi-fixed.txt"


def test_record_chapter_stamps_an_advancing_saved_at(tmp_path):
    path = tmp_path / "chapters.json"

    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1.txt")
    first_saved_at = load_chapters(path)[0].saved_at
    time.sleep(0.01)
    record_chapter(path, "ch2", "src/ch2.txt", "out/ch2.txt")

    ch2 = next(r for r in load_chapters(path) if r.chapter_id == "ch2")
    assert ch2.saved_at > first_saved_at


def test_get_recent_returns_newest_first():
    records = [
        ChapterRecord(chapter_id="ch1", source_path="s1", output_path="o1", saved_at=100.0),
        ChapterRecord(chapter_id="ch2", source_path="s2", output_path="o2", saved_at=300.0),
        ChapterRecord(chapter_id="ch3", source_path="s3", output_path="o3", saved_at=200.0),
    ]

    result = get_recent(records, 2)

    assert [r.chapter_id for r in result] == ["ch2", "ch3"]


def test_get_recent_truncates_when_fewer_than_n_exist():
    records = [ChapterRecord(chapter_id="ch1", source_path="s1", output_path="o1", saved_at=1.0)]

    assert len(get_recent(records, 5)) == 1


def test_get_recent_on_empty_list_returns_empty():
    assert get_recent([], 5) == []


def test_get_recent_non_positive_n_returns_empty():
    records = [ChapterRecord(chapter_id="ch1", source_path="s1", output_path="o1", saved_at=1.0)]

    assert get_recent(records, 0) == []
    assert get_recent(records, -1) == []
