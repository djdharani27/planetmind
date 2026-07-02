from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.logging_config import logger
from backend.database.database import init_db
from backend.api.routes.documents import router as documents_router
from backend.api.routes.pipeline import router as pipeline_router
from backend.api.routes.search import router as search_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.dashboard import router as dashboard_router
from backend.api.routes.maintenance import router as maintenance_router
from backend.api.routes.compliance import router as compliance_router
from backend.api.routes.lessons import router as lessons_router
from backend.api.routes.graph_api import router as graph_router
from backend.api.routes.admin import router as admin_router
from backend.api.routes.agent import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Initialize Graphiti (best-effort, non-blocking)
    try:
        from backend.graphiti.service import get_graphiti
        graphiti = get_graphiti()
        await graphiti.initialize()
        logger.info("Graphiti knowledge graph initialized")
    except Exception as e:
        logger.warning(f"Graphiti initialization deferred: {e}")

    logger.info(f"{settings.app_name} v{settings.app_version} starting up")
    yield
    logger.info(f"{settings.app_name} shutting down")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

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
app.include_router(maintenance_router)
app.include_router(compliance_router)
app.include_router(lessons_router)
app.include_router(graph_router)
app.include_router(agent_router)
app.include_router(admin_router)

settings.processed_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage/processed", StaticFiles(directory=str(settings.processed_dir)), name="processed")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
