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
