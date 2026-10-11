"""
FastAPI entrypoint.

- Creates tables on startup
- Registers routers
- /health endpoint for Render + quick checks
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routes import patients, vapi

# ---- Logging (Render captures stdout) ----
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables. Shutdown: nothing (engine handles pool)."""
    logger.info("Creating database tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Patient Registration Voice AI Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# ---- Routers ----
app.include_router(patients.router)
app.include_router(vapi.router)
# (vapi.router will be added in Step 5)


# ---- Health check ----
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}