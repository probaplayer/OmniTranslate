import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ChapterRecord:
    chapter_id: str
    source_path: str
    output_path: str
    saved_at: float


def load_chapters(path: str | Path) -> list[ChapterRecord]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ChapterRecord(**record) for record in data.get("chapters", [])]


def save_chapters(path: str | Path, records: list[ChapterRecord]) -> None:
    path = Path(path)
    path.write_text(
        json.dumps({"chapters": [asdict(r) for r in records]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_chapter(path: str | Path, chapter_id: str, source_path: str, output_path: str) -> None:
    records = [r for r in load_chapters(path) if r.chapter_id != chapter_id]
    records.append(
        ChapterRecord(
            chapter_id=chapter_id,
            source_path=source_path,
            output_path=output_path,
            saved_at=time.time(),
        )
    )
    save_chapters(path, records)


def get_recent(records: list[ChapterRecord], n: int) -> list[ChapterRecord]:
    if n <= 0:
        return []
    return sorted(records, key=lambda r: r.saved_at, reverse=True)[:n]
