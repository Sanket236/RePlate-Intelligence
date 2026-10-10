"""RePlate Intelligence — FastAPI application entry-point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION, CORS_ORIGINS
from app.db.database import init_db

STATIC_DIR = Path(__file__).parent.parent / "static"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (replaces deprecated on_event) ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database…")
    init_db()
    logger.info("Database ready.")
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
from app.api import health, dataset, predictions, food, recipients, agent  # noqa: E402

app.include_router(health.router)
app.include_router(dataset.router)
app.include_router(predictions.router)
app.include_router(food.router)
app.include_router(recipients.router)
app.include_router(agent.router)


# ── Static files & frontend ───────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {
        "message": "RePlate Intelligence backend is running.",
        "docs": "/docs",
        "health": "/api/health",
    }
