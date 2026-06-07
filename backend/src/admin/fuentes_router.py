from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.fuentes import Fuente, FuenteSeed
from src.models.noticias import Noticia
from src.admin.schemas import FuenteCreate, FuenteUpdate, SeedCreate

router = APIRouter(tags=["admin-fuentes"])


@router.get("/fuentes")
async def list_fuentes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fuente).order_by(Fuente.nombre))
    fuentes = []
    for f in result.scalars().all():
        seed_result = await db.execute(
            select(func.count()).select_from(FuenteSeed).where(FuenteSeed.id_fuente == f.id)
        )
        seed_count = seed_result.scalar()
        news_result = await db.execute(
            select(func.count()).select_from(Noticia).where(Noticia.id_fuente == f.id)
        )
        news_count = news_result.scalar()
        fuentes.append({
            "id": f.id,
            "nombre": f.nombre,
            "slug": f.slug,
            "url_base": f.url_base,
            "activa": f.activa,
            "confiabilidad": f.confiabilidad,
            "notas": f.notas,
            "seeds_count": seed_count,
            "noticias_count": news_count,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    return fuentes


@router.post("/fuentes", status_code=status.HTTP_201_CREATED)
async def create_fuente(data: FuenteCreate, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    fuente = Fuente(
        nombre=data.nombre,
        slug=data.slug,
        url_base=data.url_base,
        confiabilidad=data.confiabilidad,
        created_at=now,
        updated_at=now,
    )
    db.add(fuente)
    await db.commit()
    await db.refresh(fuente)
    return {"id": fuente.id, "nombre": fuente.nombre, "slug": fuente.slug}


@router.put("/fuentes/{fuente_id}")
async def update_fuente(fuente_id: int, data: FuenteUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fuente).where(Fuente.id == fuente_id))
    fuente = result.scalar_one_or_none()
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(fuente, key, value)
    fuente.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/fuentes/{fuente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fuente(fuente_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(FuenteSeed).where(FuenteSeed.id_fuente == fuente_id))
    result = await db.execute(delete(Fuente).where(Fuente.id == fuente_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    await db.commit()


@router.get("/fuentes/{fuente_id}/seeds")
async def list_seeds(fuente_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FuenteSeed)
        .where(FuenteSeed.id_fuente == fuente_id)
        .order_by(FuenteSeed.prioridad)
    )
    return [
        {
            "id": s.id,
            "tipo_seed": s.tipo_seed,
            "url_seed": s.url_seed,
            "scope_geografico": s.scope_geografico,
            "activa": s.activa,
            "prioridad": s.prioridad,
        }
        for s in result.scalars().all()
    ]


@router.post("/fuentes/{fuente_id}/seeds", status_code=status.HTTP_201_CREATED)
async def create_seed(fuente_id: int, data: SeedCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fuente).where(Fuente.id == fuente_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    seed = FuenteSeed(
        id_fuente=fuente_id,
        tipo_seed=data.tipo_seed,
        url_seed=data.url_seed,
        scope_geografico=data.scope_geografico,
        prioridad=data.prioridad,
        created_at=datetime.now(timezone.utc),
    )
    db.add(seed)
    await db.commit()
    await db.refresh(seed)
    return {"id": seed.id, "tipo_seed": seed.tipo_seed, "url_seed": seed.url_seed}


@router.delete("/fuentes/{fuente_id}/seeds/{seed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seed(fuente_id: int, seed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        delete(FuenteSeed).where(FuenteSeed.id == seed_id, FuenteSeed.id_fuente == fuente_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Seed no encontrado")
    await db.commit()
