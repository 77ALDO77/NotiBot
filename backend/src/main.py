import logging
from contextlib import asynccontextmanager

import nltk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import engine
from src.api.router import api_router
from src.auth.router import router as auth_router
from src.admin.router import router as admin_router
from src.rag.router import router as rag_router

logger = logging.getLogger(__name__)


def _init_nltk():
    for resource in ("stopwords", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{resource}" if resource == "punkt_tab" else f"corpora/{resource}")
        except LookupError:
            logger.info("Descargando NLTK %s...", resource)
            nltk.download(resource, quiet=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _init_nltk()
    yield
    await engine.dispose()


app = FastAPI(
    title="NotiBot API",
    description="Backend para la plataforma de noticias inteligentes de Lima y Callao",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["root"])
async def root():
    return {"service": "NotiBot API", "status": "running"}
