"""Paths and runtime settings. At runtime nothing calls an external service; models run in local Ollama."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("BB_DATA_ROOT", r"E:\blue-balance-data"))
RAW = DATA_ROOT / "raw"
PROCESSED = REPO / "data" / "processed"
SYNTHETIC = REPO / "data" / "synthetic"
DB_PATH = Path(os.environ.get("BB_DB", str(DATA_ROOT / "bb.sqlite")))

OLLAMA_URL = os.environ.get("BB_OLLAMA_URL", "http://127.0.0.1:11434")
AGENT_MODEL = "qwen3.5:4b"
EXTRACT_MODEL = "gemma4:e4b-it-qat"
LLM_OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 8192}

REGION_ID = "KRK"
LABELS = ("Observed", "Simulated", "Hypothesis", "Field-verified")
