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

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class CreateWorkspaceRequest(BaseModel):
    name: str
    source_lang: str = ""
    target_lang: str = ""


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
        raise HTTPException(status_code=409, detail=str(exc))
    return {"name": body.name}


@app.get("/api/workspaces/{name}")
def get_workspace_graph(name: str):
    try:
        return workspace.open_workspace(name)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.put("/api/workspaces/{name}/graph")
def put_workspace_graph(name: str, graph: dict):
    try:
        workspace.save_graph(name, graph)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok"}


@app.delete("/api/workspaces/{name}")
def delete_workspace(name: str):
    try:
        workspace.delete_workspace(name)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok"}


@app.websocket("/ws/run/{workspace_name}")
async def ws_run(websocket: WebSocket, workspace_name: str):
    await websocket.accept()
    data = await websocket.receive_json()
    graph = data["graph"]

    event_queue: "queue.Queue" = queue.Queue()

    def on_event(event):
        event_queue.put(event)

    def worker():
        try:
            run_graph(graph["nodes"], graph["links"], on_event=on_event)
        except GraphValidationError as exc:
            event_queue.put({"event": "validation_error", "message": str(exc)})
        except Exception as exc:
            event_queue.put({"event": "runtime_error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    loop = asyncio.get_event_loop()
    while True:
        event = await loop.run_in_executor(None, event_queue.get)
        if event is None:
            break
        await websocket.send_json(event)

    await websocket.close()


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
