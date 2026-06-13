import os
from contextlib import asynccontextmanager

import pytesseract
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.routers import admin, analysis, anomalies, auth, dashboard, dev, duplicates, health, invoices, notifications, settings
from app.scheduler import scheduler, start_scheduler
from app.utils.seed_thresholds import seed_default_thresholds


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    async with AsyncSessionLocal() as db:
        await seed_default_thresholds(db)
    start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="FraudGuard AI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(invoices.router)
app.include_router(analysis.router)
app.include_router(anomalies.router)
app.include_router(dashboard.router)
app.include_router(duplicates.router)
app.include_router(dev.router)
app.include_router(notifications.router)
app.include_router(settings.router)


@app.get("/")
def root():
    return {"message": "FraudGuard AI API"}
