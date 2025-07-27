from fastapi import FastAPI
from app.api.endpoints import compare
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,  # Change to DEBUG for more verbose output if needed
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)  # Get logger for this module


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    The database is initialized when its module is first imported.
    """
    logger.info("API is starting up...")  # Use logger instead of print
    yield
    logger.info("API is shutting down...")  # Use logger instead of print


app = FastAPI(
    title="Response Comparison API",
    description="Compares responses between two endpoints (GET/POST) and stores results.",
    version="1.0.0",
    lifespan=lifespan  # Modern way to set the lifespan context
)

# Include all routes from the compare endpoint module
app.include_router(compare.router, prefix="/api/v1")


@app.get("/")
def health_check():
    """A simple health check endpoint."""
    return {"status": "ok"}
