# main.py

from fastapi import FastAPI
from app.api.endpoints import compare  # your router module
from app.data.db import DBHandler

app = FastAPI(
    title="Response Comparison API",
    description="Compares responses between two endpoints (GET/POST) and stores results.",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    # initializes the DB handler on startup
    DBHandler()


# Include routes
app.include_router(compare.router, prefix="/api/v1")  # mounts all comparison-related routes.


@app.get("/")
def health_check():
    return {"status": "ok"}
