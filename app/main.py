from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.routes import planner
from app.utils.config import get_settings

app = FastAPI(
    title="AI Day Planner Agent",
    version="0.1.0",
    description=(
        "AI planner backend that parses a user's request, checks weather, finds nearby places, "
        "and optionally creates a calendar event after confirmation."
    ),
)

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


@app.get("/health", summary="Health check", description="Returns a simple status payload to confirm the API is running.")
def health_check() -> dict[str, str]:
    """Return a lightweight health status for liveness checks and deployment probes."""
    return {"status": "ok"}
