from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "database": "connected"}


@api_router.get("/news", tags=["news"])
async def list_news():
    return {"items": [], "total": 0}
