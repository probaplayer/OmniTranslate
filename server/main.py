from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
