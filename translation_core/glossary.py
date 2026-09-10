import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class GlossaryEntry:
    term: str
    translation: str
    note: str
    chapter_id: str


def load_glossary(path: str | Path) -> list[GlossaryEntry]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [GlossaryEntry(**entry) for entry in data.get("entries", [])]


def save_glossary(path: str | Path, entries: list[GlossaryEntry]) -> None:
    path = Path(path)
    path.write_text(
        json.dumps({"entries": [asdict(e) for e in entries]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_relevant_entries(entries: list[GlossaryEntry], text: str) -> list[GlossaryEntry]:
    return [e for e in entries if e.term in text]
