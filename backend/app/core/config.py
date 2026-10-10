"""Application configuration via environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'foodbridge.db'}",
)

# ── ML model artefacts ────────────────────────────────────────────────────────
MODELS_DIR: Path = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH: Path = MODELS_DIR / "food_waste_pipeline.joblib"
METADATA_PATH: Path = MODELS_DIR / "feature_metadata.json"

# ── Dataset ───────────────────────────────────────────────────────────────────
DATASET_DIR: Path = BASE_DIR.parent / "dataset"
TRAIN_CSV: Path = DATASET_DIR / "train.csv"
TEST_CSV: Path = DATASET_DIR / "test.csv"

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

# ── Optional LLM integration ─────────────────────────────────────────────────
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_ENABLED: bool = bool(OPENAI_API_KEY)

# ── App metadata ─────────────────────────────────────────────────────────────
APP_TITLE = "RePlate Intelligence"
APP_DESCRIPTION = (
    "AI-powered platform that predicts food waste, connects surplus food with "
    "recipients, and helps organizations make smarter sustainability decisions. "
    "(aligned with UN SDG 12 & SDG 2)"
)
APP_VERSION = "1.0.0"

# ── Matching / safety rules ───────────────────────────────────────────────────
# Minimum hours before expiry to still consider food safe for redistribution
MIN_HOURS_BEFORE_EXPIRY: int = int(os.getenv("MIN_HOURS_BEFORE_EXPIRY", "4"))
# Safety margin applied to recipient capacity (never fill above this fraction)
CAPACITY_SAFETY_MARGIN: float = float(
    os.getenv("CAPACITY_SAFETY_MARGIN", "0.95")
)

# ── Pagination defaults ───────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ── Random seed for ML reproducibility ───────────────────────────────────────
RANDOM_SEED: int = 42
