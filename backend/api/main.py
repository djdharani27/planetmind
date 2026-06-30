from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.logging_config import logger
from backend.database.database import init_db


app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    logger.info(f"{settings.app_name} v{settings.app_version} starting up")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
