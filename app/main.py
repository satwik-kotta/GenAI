from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.routes import planner
from app.utils.config import get_settings

app = FastAPI(title="AI Day Planner Agent", version="0.1.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(planner.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
