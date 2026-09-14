import json
import re
import shutil
from pathlib import Path

# Anchored to this module's own location (matching server/main.py's WEB_DIR
# convention) so the workspaces directory never depends on the process cwd.
WORKSPACES_ROOT = Path(__file__).resolve().parent.parent / "workspaces"

_DEFAULT_GRAPH = {"nodes": [], "links": []}

_DEFAULT_AGENT_FILE = (
    "# Hướng dẫn dịch\n\n"
    "Dịch sang tiếng Việt, giữ văn phong tự nhiên, nhất quán tên riêng/thuật ngữ.\n"
)

_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


class WorkspaceError(Exception):
    """Base error: the workspace exists when it shouldn't, or vice versa."""


class InvalidWorkspaceNameError(WorkspaceError):
    """The given name is not an acceptable workspace name at all."""


class CorruptWorkspaceError(WorkspaceError):
    """The workspace exists but its graph.json content is unusable."""


class InvalidGraphError(WorkspaceError):
    """The graph handed in for saving is not a well-shaped graph object."""


class InvalidOutputPathError(WorkspaceError):
    """The given output-file path is not a path inside that workspace's output dir."""


class NotTextFileError(WorkspaceError):
    """The output file exists but isn't decodable as UTF-8 text."""


def _is_valid_workspace_name(name: str) -> bool:
    """Check a workspace name against a strict allowlist pattern.

    Only allows alphanumeric characters, hyphen, and underscore to prevent
    path traversal, absolute paths, drive letters, and other exploits.
    `fullmatch` (not `match`) is required: `match` with a `$` anchor also
    accepts a trailing newline, which would then blow up in `mkdir`.

    Non-strings are simply invalid rather than a TypeError from the regex, so
    this stays a total predicate for any caller.
    """
    if not isinstance(name, str):
        return False
    return _NAME_PATTERN.fullmatch(name) is not None


def _validate_workspace_name(name: str) -> None:
    # A non-string (most plausibly None, from a run_graph caller that omitted
    # workspace_name while the graph contains a NEEDS_WORKSPACE node) used to
    # reach the regex and surface as a raw "expected string or bytes-like
    # object" TypeError. Name the actual problem instead.
    if not isinstance(name, str):
        raise InvalidWorkspaceNameError(
            f"Workspace name must be a string, got {type(name).__name__}"
        )
    if not _is_valid_workspace_name(name):
        raise InvalidWorkspaceNameError(
            f"Workspace name must contain only letters, digits, hyphen, and underscore; got '{name}'"
        )


def _workspace_dir(name: str) -> Path:
    _validate_workspace_name(name)
    return WORKSPACES_ROOT / name


def get_workspace_path(name: str, *parts: str) -> Path:
    return _workspace_dir(name).joinpath(*parts)


def list_workspaces() -> list:
    if not WORKSPACES_ROOT.exists():
        return []
    # Skip directories whose names would fail validation (e.g. a folder
    # created by hand with a space in it) -- listing them only produces a
    # 400 when the user clicks them in the picker.
    return sorted(
        p.name
        for p in WORKSPACES_ROOT.iterdir()
        if p.is_dir() and _is_valid_workspace_name(p.name)
    )


def create_workspace(name: str, source_lang: str = "", target_lang: str = "") -> None:
    ws_dir = _workspace_dir(name)
    if ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' already exists")
    ws_dir.mkdir(parents=True)
    (ws_dir / "chapters").mkdir()
    (ws_dir / "output").mkdir()
    (ws_dir / "config.json").write_text(
        json.dumps(
            {"name": name, "source_lang": source_lang, "target_lang": target_lang},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (ws_dir / "graph.json").write_text(json.dumps(_DEFAULT_GRAPH), encoding="utf-8")
    (ws_dir / "agent.md").write_text(_DEFAULT_AGENT_FILE, encoding="utf-8")
    (ws_dir / "glossary.json").write_text(json.dumps({"entries": []}), encoding="utf-8")
    (ws_dir / "chapters.json").write_text(json.dumps({"chapters": []}), encoding="utf-8")


def open_workspace(name: str) -> dict:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    graph_path = ws_dir / "graph.json"
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        raise CorruptWorkspaceError(
            f"Workspace '{name}' has a corrupted graph.json: {exc}"
        )
    if not isinstance(graph, dict):
        raise CorruptWorkspaceError(
            f"Workspace '{name}' graph.json must be a JSON object (dict), got {type(graph).__name__}"
        )
    if "nodes" not in graph or "links" not in graph:
        raise CorruptWorkspaceError(
            f"Workspace '{name}' graph.json missing 'nodes'/'links'"
        )
    return graph


def save_graph(name: str, graph: dict) -> None:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    # Reject anything open_workspace could not read back, so a client cannot
    # brick a workspace by saving a shape that makes it permanently
    # un-openable.
    if not isinstance(graph, dict):
        raise InvalidGraphError(
            f"Graph must be a JSON object (dict), got {type(graph).__name__}"
        )
    if "nodes" not in graph or "links" not in graph:
        raise InvalidGraphError("Graph must contain both 'nodes' and 'links' keys")
    (ws_dir / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def delete_workspace(name: str) -> None:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    shutil.rmtree(ws_dir)


def rename_workspace(old_name: str, new_name: str) -> None:
    old_dir = _workspace_dir(old_name)
    if not old_dir.exists():
        raise WorkspaceError(f"Workspace '{old_name}' does not exist")
    new_dir = _workspace_dir(new_name)
    if new_dir.exists():
        raise WorkspaceError(f"Workspace '{new_name}' already exists")
    old_dir.rename(new_dir)

    # config.json's "name" field is never read anywhere else in the app --
    # this is purely so the file doesn't sit there with a stale name if
    # someone inspects it by hand. A failure here must not undo the rename
    # itself, which already succeeded.
    config_path = new_dir / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["name"] = new_name
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (OSError, json.JSONDecodeError):
        pass


def list_output_files(name: str) -> list:
    """List every file under this workspace's output/ dir, recursively.

    Returns dicts with a `/`-joined relative path (stable across OSes, and
    exactly the path a client echoes back to read/delete that file), size in
    bytes, and last-modified time as a Unix timestamp. A workspace's output/
    dir always exists (created by create_workspace) unless something removed
    it by hand -- treated the same as "no files yet" rather than an error.
    """
    output_dir = get_workspace_path(name, "output")
    if not get_workspace_path(name).exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    if not output_dir.exists():
        return []
    files = []
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        files.append(
            {
                "path": "/".join(path.relative_to(output_dir).parts),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        )
    return sorted(files, key=lambda f: f["path"])


def _resolve_output_file_path(name: str, relative_path: str) -> Path:
    """Resolve a client-given relative path to a real path inside output/.

    Rejects anything that would escape output/ (absolute paths, `..`
    segments, symlink shenanigans) by resolving both paths and checking
    containment -- the same class of bug workspace names are guarded
    against, just for a path with multiple segments instead of one name.
    """
    output_dir = get_workspace_path(name, "output")
    if not get_workspace_path(name).exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    candidate = (output_dir / relative_path).resolve()
    if not candidate.is_relative_to(output_dir.resolve()):
        raise InvalidOutputPathError(f"Invalid output file path: '{relative_path}'")
    return candidate


def read_output_file(name: str, relative_path: str) -> str:
    path = _resolve_output_file_path(name, relative_path)
    if not path.is_file():
        raise WorkspaceError(f"Output file '{relative_path}' does not exist")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise NotTextFileError(f"Output file '{relative_path}' is not a text file")


def delete_output_file(name: str, relative_path: str) -> None:
    path = _resolve_output_file_path(name, relative_path)
    if not path.is_file():
        raise WorkspaceError(f"Output file '{relative_path}' does not exist")
    path.unlink()
