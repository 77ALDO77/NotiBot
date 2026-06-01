import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import settings
from src.models.pipeline import ScrapingLog

router = APIRouter(tags=["admin-scraping"])
_running_scrapers: dict = {}


@router.get("/scraping-logs")
async def list_scraping_logs(
    db: AsyncSession = Depends(get_db),
    nivel: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    stmt = select(ScrapingLog).order_by(ScrapingLog.created_at.desc())
    if nivel:
        stmt = stmt.where(ScrapingLog.nivel == nivel)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    logs = [
        {
            "id": l.id,
            "id_fuente": l.id_fuente,
            "id_noticia": l.id_noticia,
            "nivel": l.nivel,
            "mensaje": l.mensaje,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in result.scalars().all()
    ]
    return {"items": logs, "total": total}


@router.get("/scraping/logs")
async def get_scraping_logs_rich(
    db: AsyncSession = Depends(get_db),
    fecha: Optional[str] = Query(None, description="YYYY-MM-DD"),
    nivel: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    stmt = select(ScrapingLog).order_by(ScrapingLog.created_at.desc())
    if fecha:
        stmt = stmt.where(ScrapingLog.metadata_.op("->>")("fecha") == fecha)
    if nivel:
        stmt = stmt.where(ScrapingLog.nivel == nivel)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    logs = []
    for l in result.scalars().all():
        meta = l.metadata_ or {}
        logs.append({
            "id": l.id, "id_fuente": l.id_fuente, "id_noticia": l.id_noticia,
            "nivel": l.nivel, "mensaje": l.mensaje,
            "fecha": meta.get("fecha"), "tipo": meta.get("tipo"),
            "insertadas": meta.get("insertadas"),
            "errores": meta.get("errores"),
            "urls_totales": meta.get("urls_totales"),
            "filtradas_geo": meta.get("filtradas_geo"),
            "duplicadas": meta.get("duplicadas"),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    return {"items": logs, "total": total, "limit": limit, "offset": offset}


@router.get("/scraping/logs/daily")
async def get_daily_summaries(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(30, le=90),
):
    result = await db.execute(
        select(ScrapingLog)
        .where(ScrapingLog.metadata_.op("->>")("tipo") == "day_summary")
        .order_by(ScrapingLog.created_at.desc())
        .limit(limit)
    )
    summaries = []
    for l in result.scalars().all():
        meta = l.metadata_ or {}
        summaries.append({
            "id": l.id,
            "fecha": meta.get("fecha"),
            "urls_totales": meta.get("urls_totales"),
            "filtradas_geo": meta.get("filtradas_geo"),
            "insertadas": meta.get("insertadas"),
            "errores": meta.get("errores"),
            "duplicadas": meta.get("duplicadas"),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    return {"items": summaries, "total": len(summaries)}


@router.get("/scraping/logs/live")
async def get_live_logs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(30, le=100),
):
    result = await db.execute(
        select(ScrapingLog)
        .order_by(ScrapingLog.created_at.desc())
        .limit(limit)
    )
    logs = []
    for l in result.scalars().all():
        meta = l.metadata_ or {}
        logs.append({
            "id": l.id,
            "nivel": l.nivel,
            "mensaje": l.mensaje,
            "fecha": meta.get("fecha"),
            "tipo": meta.get("tipo"),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    return {"items": list(reversed(logs)), "total": len(logs)}


@router.get("/scraping/status")
async def get_scraping_status():
    state = _running_scrapers.get("default", {})
    running = bool(state.get("pid"))
    return {
        "running": running,
        "current_day": state.get("current_day"),
        "lines_count": state.get("lines", 0),
        "started_at": state.get("started_at", {}).isoformat() if state.get("started_at") else None,
        "command": state.get("command", ""),
    }


@router.post("/scraping/run")
async def trigger_scraping(
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD, single day"),
    today: bool = Query(False),
    daily: bool = Query(False),
):
    import asyncio, sys

    cmd = [sys.executable, "-m", "src.scraper.main", "--db"]
    current_day = date or start or (datetime.now().strftime("%Y-%m-%d") if today else None)

    if today:
        cmd.append("--today")
    elif date:
        cmd.extend(["--date", date])
    elif start:
        cmd.extend(["--start", start])
        if end:
            cmd.extend(["--end", end])
    if daily:
        cmd.append("--daily")

    _running_scrapers["default"] = {
        "pid": True,
        "current_day": current_day,
        "lines": 0,
        "started_at": datetime.now(timezone.utc),
        "command": " ".join(cmd),
    }

    asyncio.create_task(_run_scraper_async(cmd, current_day))
    return {"status": "started", "command": " ".join(cmd)}


async def _run_scraper_async(cmd: list, current_day: str | None = None):
    import asyncio as aio
    from src.core.database import AsyncSessionLocal

    proc = await aio.create_subprocess_exec(
        *cmd,
        stdout=aio.subprocess.PIPE,
        stderr=aio.subprocess.STDOUT,
        env={
            **__import__("os").environ,
            "DATABASE_URL": settings.DATABASE_URL,
            "PYTHONUNBUFFERED": "1",
        },
    )

    async def _insert_live_log(nivel: str, mensaje: str, day: str | None = None):
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO public.scraping_logs (id_fuente, nivel, mensaje, metadata, created_at)
                        VALUES (NULL, :nivel, :mensaje, CAST(:meta AS jsonb), :created_at)
                    """),
                    {
                        "nivel": nivel,
                        "mensaje": mensaje[:500],
                        "meta": json.dumps({"tipo": "live", "fecha": day}) if day else None,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                await db.commit()
        except Exception as e:
            import sys
            print(f"[SCRAPER_LIVE_LOG_ERROR] {e}", file=sys.stderr, flush=True)

    state = _running_scrapers.get("default", {})

    try:
        if proc.stdout:
            async for line in proc.stdout:
                raw_line = line.decode("utf-8", errors="replace").strip()
                if not raw_line:
                    continue

                nivel = "error" if "✗" in raw_line or "ERROR" in raw_line.lower() else \
                        "warning" if "WARN" in raw_line.lower() or "⚠" in raw_line else "info"

                await _insert_live_log(nivel, raw_line, current_day)

                state["lines"] = state.get("lines", 0) + 1
                _running_scrapers["default"] = state

                if "DIA:" in raw_line and current_day is None:
                    current_day = raw_line.split("DIA:")[-1].strip()
                    state["current_day"] = current_day

        await proc.wait()
    finally:
        _running_scrapers.pop("default", None)
