from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.logging_config import logger
from backend.database.database import init_db
from backend.api.routes.documents import router as documents_router
from backend.api.routes.pipeline import router as pipeline_router
from backend.api.routes.search import router as search_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.dashboard import router as dashboard_router


app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(pipeline_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup():
    init_db()
    logger.info(f"{settings.app_name} v{settings.app_version} starting up")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
