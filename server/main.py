from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import workspace
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


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
