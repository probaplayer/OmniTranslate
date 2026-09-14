import asyncio
import os
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import workspace
from server import agent_templates
from server.executor import GraphValidationError, run_graph
from server.node_registry import list_node_metadata
from server.nodes import utility  # noqa: F401  (triggers registration)
from server.nodes import translate as translate_nodes  # noqa: F401  (triggers registration)
from translation_core import ProviderConfig, ProviderError, create_provider

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# WebSockets are not covered by the browser's same-origin policy, so any page
# the user has open could otherwise connect to the local server and submit a
# graph (which can read and write arbitrary files). Only our own origins are
# accepted; see ws_run.
_ALLOWED_ORIGINS = {"http://127.0.0.1:8000", "http://localhost:8000"}


@app.get("/")
def root():
    return RedirectResponse(url="/canvas.html")


class CreateWorkspaceRequest(BaseModel):
    name: str
    source_lang: str = ""
    target_lang: str = ""


class RenameWorkspaceRequest(BaseModel):
    new_name: str


class TestProviderRequest(BaseModel):
    base_url: str
    api_key: str
    model: str


def _workspace_http_error(
    exc: workspace.WorkspaceError, base_status: int
) -> HTTPException:
    """Map a WorkspaceError to a consistent HTTP status across endpoints.

    The specific subclasses have a fixed status regardless of endpoint: a
    rejected name is a bad request (400), and a workspace whose stored
    graph.json is unusable is unprocessable content (422). The base class
    means "exists / does not exist", whose right status depends on the
    endpoint -- 409 for POST's already-exists, 404 for the others'
    does-not-exist -- so callers pass that in as `base_status`.
    """
    if isinstance(
        exc, (workspace.InvalidWorkspaceNameError, workspace.InvalidGraphError)
    ):
        status = 400
    elif isinstance(exc, workspace.CorruptWorkspaceError):
        status = 422
    else:
        status = base_status
    return HTTPException(status_code=status, detail=str(exc))


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/nodes")
def get_nodes():
    return list_node_metadata()


@app.get("/api/agent-templates")
def get_agent_templates():
    return agent_templates.list_templates()


@app.post("/api/test-provider")
def test_provider(body: TestProviderRequest):
    """Actually exercise a Provider node's config with one real request.

    Building a provider (Provider.execute(), what running that node in a
    graph does) never touches the network -- it just stores the config, so
    a bad base_url/api_key/model would otherwise never surface until a real
    Translate/ExtractGlossary run. This is the standalone "test connection"
    button's backing endpoint: always 200, {ok, message} tells the caller
    whether the request itself succeeded.
    """
    config = ProviderConfig(
        type="openai_compatible",
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
    )
    provider = create_provider(config)
    try:
        provider.complete([{"role": "user", "content": "ping"}], max_tokens=1)
    except ProviderError as exc:
        return {"ok": False, "message": str(exc)}
    finally:
        provider.close()
    return {"ok": True}


@app.get("/api/workspaces")
def get_workspaces():
    return {"workspaces": workspace.list_workspaces()}


@app.post("/api/workspaces", status_code=201)
def post_workspace(body: CreateWorkspaceRequest):
    try:
        workspace.create_workspace(body.name, body.source_lang, body.target_lang)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 409)
    return {"name": body.name}


@app.get("/api/workspaces/{name}")
def get_workspace_graph(name: str):
    try:
        return workspace.open_workspace(name)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 404)


@app.get("/api/browse-directory")
def browse_directory(path: str = ""):
    if not path:
        entries = [
            {"name": drive.rstrip("\\/"), "path": drive}
            for drive in os.listdrives()
        ]
        return {"path": None, "parent": None, "entries": entries}

    target = Path(path).resolve()
    if not target.is_dir():
        raise HTTPException(
            status_code=400, detail="Path does not exist or is not a directory"
        )

    entries = []
    try:
        children = sorted(target.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        children = []
    for child in children:
        try:
            if child.is_dir():
                entries.append({"name": child.name, "path": str(child)})
        except PermissionError:
            continue

    # A drive root is its own parent in pathlib (Path("C:/").parent == Path("C:/")) --
    # without this check, "Up" from a drive root would loop on itself forever.
    # Instead, parent becomes None here, which tells the frontend to hide the
    # "Up" row entirely at a drive root (not to auto-jump to the drive list --
    # from here the user clears the field and reopens the picker for that).
    parent = str(target.parent) if target.parent != target else None
    return {"path": str(target), "parent": parent, "entries": entries}


@app.put("/api/workspaces/{name}/graph")
def put_workspace_graph(name: str, graph: dict):
    try:
        workspace.save_graph(name, graph)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 404)
    return {"status": "ok"}


@app.patch("/api/workspaces/{name}")
def patch_workspace(name: str, body: RenameWorkspaceRequest):
    # The base WorkspaceError (bare "does not exist" / "already exists") is
    # ambiguous here -- rename_workspace can raise it for either the old name
    # (404) or the new one (409). Resolve the old name's path first (this
    # alone validates its format, raising InvalidWorkspaceNameError -> 400 for
    # a malformed one, same as every other workspace endpoint) and check
    # existence explicitly, so the only bare WorkspaceError that can reach
    # the second except below is the new-name conflict.
    try:
        old_dir = workspace.get_workspace_path(name)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 404)
    if not old_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Workspace '{name}' does not exist"
        )
    try:
        workspace.rename_workspace(name, body.new_name)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 409)
    return {"name": body.new_name}


@app.delete("/api/workspaces/{name}")
def delete_workspace(name: str):
    try:
        workspace.delete_workspace(name)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 404)
    return {"status": "ok"}


@app.websocket("/ws/run/{workspace_name}")
async def ws_run(websocket: WebSocket, workspace_name: str):
    # A real browser always sends Origin on a WS handshake, so a mismatch
    # means a foreign page is trying to drive the local server. A missing
    # Origin means a non-browser client (TestClient, a future MCP server),
    # which is allowed.
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in _ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    data = await websocket.receive_json()
    graph = data["graph"]

    # Nothing downstream checks that the workspace named in the URL exists.
    # A NEEDS_WORKSPACE node given a nonexistent name would surface a raw,
    # unhelpful FileNotFoundError deep inside its own file I/O instead of a
    # clear validation error -- refuse the run up front instead.
    # open_workspace is the same existence check the HTTP endpoints use; it
    # also rejects invalid/traversing names.
    try:
        workspace.open_workspace(workspace_name)
    except workspace.WorkspaceError as exc:
        await websocket.send_json({"event": "validation_error", "message": str(exc)})
        await websocket.close()
        return

    event_queue: "queue.Queue" = queue.Queue()

    def on_event(event):
        event_queue.put(event)

    def worker():
        try:
            run_graph(
                graph["nodes"], graph["links"], on_event=on_event,
                workspace_name=workspace_name,
            )
        except GraphValidationError as exc:
            event_queue.put({"event": "validation_error", "message": str(exc)})
        except Exception as exc:
            event_queue.put({"event": "runtime_error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    loop = asyncio.get_running_loop()
    try:
        while True:
            event = await loop.run_in_executor(None, event_queue.get)
            if event is None:
                break
            try:
                await websocket.send_json(event)
            except Exception as exc:
                # A send that raises (an event that slipped past executor's
                # serialization guard, or a client that went away) must not
                # kill this coroutine outright: that would skip the close()
                # below and leave the client hanging forever, waiting for a
                # run_finished it can never receive. Make one best-effort
                # attempt to say why, then stop draining. The worker thread is
                # a daemon and unaffected -- it finishes its run either way.
                try:
                    await websocket.send_json(
                        {
                            "event": "runtime_error",
                            "message": f"Failed to send event: {exc}",
                        }
                    )
                except Exception:
                    pass
                break
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
