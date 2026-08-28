import json
import shutil
from pathlib import Path

WORKSPACES_ROOT = Path("workspaces")

_DEFAULT_GRAPH = {"nodes": [], "links": []}


class WorkspaceError(Exception):
    pass


def _workspace_dir(name: str) -> Path:
    return WORKSPACES_ROOT / name


def list_workspaces() -> list:
    if not WORKSPACES_ROOT.exists():
        return []
    return sorted(p.name for p in WORKSPACES_ROOT.iterdir() if p.is_dir())


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


def open_workspace(name: str) -> dict:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    graph_path = ws_dir / "graph.json"
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        raise WorkspaceError(f"Workspace '{name}' has a corrupted graph.json: {exc}")
    if "nodes" not in graph or "links" not in graph:
        raise WorkspaceError(f"Workspace '{name}' graph.json missing 'nodes'/'links'")
    return graph


def save_graph(name: str, graph: dict) -> None:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    (ws_dir / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def delete_workspace(name: str) -> None:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    shutil.rmtree(ws_dir)
