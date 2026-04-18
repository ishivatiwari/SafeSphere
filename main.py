"""SafeSphere API — Real-time crowd management AI agent.

Integrations:
- Google Gemini 2.5 Flash: AI-powered risk assessment
- Google Cloud Logging: Structured observability
- Google Cloud Firestore: Analysis history persistence
- TTL cache + GZip: Efficiency optimisations
- SlowAPI rate limiting + security headers: Hardened security
"""

import os
import json
import logging
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ── Google Cloud Logging ──────────────────────────────────────────────────────
logger = logging.getLogger("safesphere")
logger.setLevel(logging.INFO)

try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler

    _cloud_log_client = google.cloud.logging.Client()
    _cloud_handler = CloudLoggingHandler(_cloud_log_client, name="safesphere")
    logger.addHandler(_cloud_handler)
    _cloud_logging_available = True
except Exception as _cl_err:
    logging.basicConfig(level=logging.INFO)
    logger.warning("Cloud Logging unavailable, falling back to stdout: %s", _cl_err)
    _cloud_logging_available = False

# ── Google Cloud Firestore ────────────────────────────────────────────────────
_db: Optional[object] = None
_firestore_available = False

try:
    from google.cloud import firestore as _firestore_module

    _db = _firestore_module.Client()
    _firestore_available = True
    logger.info("Firestore client initialized successfully")
except Exception as _fs_err:
    logger.warning("Firestore unavailable: %s", _fs_err)

# ── Gemini client singleton ───────────────────────────────────────────────────
_gemini_client: Optional[genai.Client] = None


def get_gemini_client() -> genai.Client:
    """Return a shared Gemini client, initialising it on first call."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY environment variable is not set.",
            )
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized")
    return _gemini_client


# ── Analysis cache: LRU with 60-second TTL ───────────────────────────────────
_analysis_cache: TTLCache = TTLCache(maxsize=128, ttl=60)

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])


# ── Lifespan: warm up dependencies at startup ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("GEMINI_API_KEY"):
        try:
            get_gemini_client()
            logger.info("SafeSphere v2.0 started — all systems nominal")
        except Exception as exc:
            logger.warning("Startup warm-up failed: %s", exc)
    yield


# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title="SafeSphere API",
    description=(
        "Real-time crowd management AI Agent designed to prevent stampedes "
        "and manage large-scale events."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject OWASP-recommended security response headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Pydantic Models ───────────────────────────────────────────────────────────
class ZoneInput(BaseModel):
    """Input data for a single monitored crowd zone."""

    zone_id: str = Field(
        ..., min_length=1, max_length=20, description="Unique zone identifier (e.g. A1)"
    )
    density: float = Field(
        ..., ge=0, le=200, description="Crowd density percentage (0–200)"
    )
    movement_speed: float = Field(
        ..., ge=0, le=20, description="Average movement speed in m/s"
    )


class ZoneStatus(BaseModel):
    """AI-assessed safety status for a single zone."""

    zone_id: str
    density_level: str
    risk_level: str
    trend: str


class SafeSphereOutput(BaseModel):
    """Complete safety assessment returned by the AI agent."""

    zone_status: List[ZoneStatus]
    actions: List[str]
    alerts: List[str]


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are SafeSphere, an intelligent crowd management system designed to prevent \
stampedes and manage large-scale events like Kumbh Mela.

Your job is to analyse crowd data across multiple zones and take real-time decisions \
to ensure safety and smooth movement.

=== YOUR TASK ===
For each zone:
1. Classify density:
   - 0–40  → Low
   - 41–70 → Medium
   - 71–90 → High
   - 91+   → Critical

2. Detect risk:
   - High density + low movement = High Risk
   - Critical density             = Stampede Risk

3. Predict next state:
   - density > 80 → Increasing risk
   - Otherwise   → Stable

4. Suggest actions:
   - Redirect crowd
   - Open alternative routes
   - Trigger alerts if critical

=== RULES ===
- Always prioritise human safety
- Keep responses structured and concise
- Avoid panic-inducing language
- Think like a real-time control system
"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_cache_key(zones: List[ZoneInput]) -> str:
    """SHA-256 hash of the sorted zone payload for deterministic cache keys."""
    payload = json.dumps([z.model_dump() for z in zones], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _persist_to_firestore(zones: List[ZoneInput], result: SafeSphereOutput) -> None:
    """Best-effort write of analysis results to Firestore for history tracking."""
    if not _firestore_available or _db is None:
        return
    try:
        from google.cloud import firestore as _fs

        doc = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones_analyzed": len(zones),
            "input": [z.model_dump() for z in zones],
            "result": result.model_dump(),
            "high_risk_zones": [
                z.zone_id
                for z in result.zone_status
                if "Risk" in z.risk_level or z.density_level in ("High", "Critical")
            ],
        }
        _db.collection("analysis_history").add(doc)
        logger.info("Analysis saved to Firestore", extra={"zones": len(zones)})
    except Exception as exc:
        logger.error("Firestore write failed: %s", exc)


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post(
    "/analyze",
    response_model=SafeSphereOutput,
    summary="Analyse zone crowd data",
    description=(
        "Accepts a list of zone readings and returns an AI-powered real-time "
        "risk assessment with actionable crowd management suggestions."
    ),
)
@limiter.limit("30/minute")
async def analyze_zones(request: Request, zones: List[ZoneInput]) -> SafeSphereOutput:
    if not zones:
        raise HTTPException(
            status_code=422, detail="At least one zone must be provided."
        )

    # Cache look-up
    cache_key = _make_cache_key(zones)
    if cache_key in _analysis_cache:
        logger.info("Cache hit", extra={"cache_key": cache_key[:8]})
        return _analysis_cache[cache_key]

    client = get_gemini_client()
    user_prompt = (
        f"=== INPUT ===\nYou will receive zone data in this format:\n"
        f"{[z.model_dump() for z in zones]}"
    )
    logger.info("Gemini analysis started", extra={"zones": len(zones)})

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=SafeSphereOutput,
                temperature=0.1,
            ),
        )
        result = SafeSphereOutput.model_validate_json(response.text)

        # Store in cache + Firestore
        _analysis_cache[cache_key] = result
        _persist_to_firestore(zones, result)

        logger.info(
            "Analysis complete",
            extra={"zones": len(zones), "alerts": len(result.alerts)},
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Gemini analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/history",
    summary="Retrieve analysis history",
    description="Returns the most recent crowd analysis records stored in Firestore.",
)
@limiter.limit("20/minute")
async def get_history(request: Request, limit: int = 10):
    if not _firestore_available or _db is None:
        raise HTTPException(
            status_code=503,
            detail="History storage is not available. Firestore may not be configured.",
        )
    try:
        from google.cloud import firestore as _fs

        docs = (
            _db.collection("analysis_history")
            .order_by("timestamp", direction=_fs.Query.DESCENDING)
            .limit(min(limit, 50))
            .stream()
        )
        history = [doc.to_dict() for doc in docs]
        return {"count": len(history), "records": history}
    except Exception as exc:
        logger.error("Firestore read failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/health",
    summary="Health check",
    description="Returns service health status and dependency availability.",
)
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "gemini_ready": _gemini_client is not None,
            "firestore": _firestore_available,
            "cloud_logging": _cloud_logging_available,
            "cache_size": len(_analysis_cache),
            "cache_maxsize": _analysis_cache.maxsize,
        },
    }


# ── Static files & root ───────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def read_root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
