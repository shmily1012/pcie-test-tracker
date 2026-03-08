from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import engine, Base
from .routers import test_cases, executions, comments, dashboard, import_export, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="PCIe Test Tracker", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_cases.router)
app.include_router(executions.router)
app.include_router(comments.router)
app.include_router(dashboard.router)
app.include_router(import_export.router)
app.include_router(audit.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

# Serve frontend static files
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "../../frontend/dist")
if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
