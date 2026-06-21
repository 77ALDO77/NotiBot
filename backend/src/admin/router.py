from fastapi import APIRouter, Depends

from src.auth.dependencies import require_admin
from src.admin.analytics_router import router as analytics_router
from src.admin.fuentes_router import router as fuentes_router
from src.admin.pipeline_router import router as pipeline_router
from src.admin.scraping_router import router as scraping_router
from src.admin.stats_router import router as stats_router
from src.admin.noticias_router import router as noticias_router
from src.admin.vectores_router import router as vectores_router
from src.admin.backup_router import router as backup_router

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
router.include_router(fuentes_router)
router.include_router(pipeline_router)
router.include_router(scraping_router)
router.include_router(stats_router)
router.include_router(noticias_router)
router.include_router(vectores_router)
router.include_router(analytics_router)
router.include_router(backup_router, prefix="/backup")
