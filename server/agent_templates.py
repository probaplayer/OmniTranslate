import re
from pathlib import Path

AGENTS_ROOT = Path(__file__).resolve().parent.parent / "agents"
_SLUG_PATTERN = re.compile(r"[a-z0-9_-]+")


def _is_valid_slug(value: str) -> bool:
    return isinstance(value, str) and _SLUG_PATTERN.fullmatch(value) is not None


def list_templates() -> dict[str, list[str]]:
    if not AGENTS_ROOT.exists():
        return {}
    result = {}
    for lang_dir in sorted(AGENTS_ROOT.iterdir()):
        if not lang_dir.is_dir() or not _is_valid_slug(lang_dir.name):
            continue
        genres = sorted(
            p.stem for p in lang_dir.glob("*.md") if _is_valid_slug(p.stem)
        )
        if genres:
            result[lang_dir.name] = genres
    return result


def resolve_template_path(template: str) -> Path:
    parts = template.split("/")
    if len(parts) != 2:
        raise ValueError(f"Malformed template id: '{template}' (expected '<lang>/<genre>')")
    lang, genre = parts
    if not _is_valid_slug(lang) or not _is_valid_slug(genre):
        raise ValueError(f"Malformed template id: '{template}'")
    path = AGENTS_ROOT / lang / f"{genre}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Agent template not found: '{template}'")
    return path
