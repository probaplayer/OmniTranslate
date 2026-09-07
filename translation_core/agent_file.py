from pathlib import Path


def load_agent_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def save_agent_file(path: str | Path, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")
