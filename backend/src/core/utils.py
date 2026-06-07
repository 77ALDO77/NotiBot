from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def paginate(
    db: AsyncSession,
    stmt,
    *,
    limit: int = 20,
    offset: int = 0,
    serializer: callable = lambda row: row,
) -> dict[str, Any]:
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    items = [serializer(row) for row in result.all()]

    return {"items": items, "total": total}
