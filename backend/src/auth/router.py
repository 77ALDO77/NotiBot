from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.others import Usuario
from src.auth import schemas, service
from src.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    login_data: schemas.LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario).where(Usuario.correo == login_data.correo)
    )
    user = result.scalar_one_or_none()

    if not user or not service.verify_password(login_data.password, user.hash_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos",
        )

    if user.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    user.ultimo_acceso = datetime.now(timezone.utc)
    await db.commit()

    access_token = service.create_access_token(
        data={"sub": str(user.id), "rol": user.rol}
    )

    return schemas.TokenResponse(
        access_token=access_token,
        user=schemas.UserResponse.model_validate(user),
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: Usuario = Depends(get_current_user)):
    return schemas.UserResponse.model_validate(current_user)


@router.post("/register", response_model=schemas.UserResponse, dependencies=[Depends(require_admin)])
async def register_user(
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Usuario).where(
            (Usuario.correo == user_data.correo)
            | (Usuario.nombre_usuario == user_data.nombre_usuario)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo o nombre de usuario ya existe",
        )

    user = Usuario(
        nombre_usuario=user_data.nombre_usuario,
        correo=user_data.correo,
        hash_password=service.hash_password(user_data.password),
        rol=user_data.rol,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return schemas.UserResponse.model_validate(user)
