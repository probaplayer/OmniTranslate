import asyncio
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import workspace
from server.executor import GraphValidationError, run_graph
from server.node_registry import list_node_metadata
from server.nodes import utility  # noqa: F401  (triggers registration)
from server.nodes import translate as translate_nodes  # noqa: F401  (triggers registration)

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# WebSockets are not covered by the browser's same-origin policy, so any page
# the user has open could otherwise connect to the local server and submit a
# graph (which can read and write arbitrary files). Only our own origins are
# accepted; see ws_run.
_ALLOWED_ORIGINS = {"http://127.0.0.1:8000", "http://localhost:8000"}


class CreateWorkspaceRequest(BaseModel):
    name: str
    source_lang: str = ""
    target_lang: str = ""


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


@app.put("/api/workspaces/{name}/graph")
def put_workspace_graph(name: str, graph: dict):
    try:
        workspace.save_graph(name, graph)
    except workspace.WorkspaceError as exc:
        raise _workspace_http_error(exc, 404)
    return {"status": "ok"}


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

    # Nothing downstream checks that the workspace named in the URL exists, and
    # the NEEDS_WORKSPACE nodes happily create what they need on demand
    # (chromadb.PersistentClient auto-creates parent directories), so a typo'd
    # name would materialise an orphaned workspaces/<name>/rag_index/ with no
    # config.json or graph.json -- which then shows up in the workspace picker
    # and errors when clicked. Refuse the run before the worker thread (and any
    # filesystem access) starts. open_workspace is the same existence check the
    # HTTP endpoints use; it also rejects invalid/traversing names.
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
