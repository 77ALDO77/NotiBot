from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    nombre_usuario: str
    correo: str
    password: str
    rol: str = "lector"


class UserResponse(BaseModel):
    id: int
    nombre_usuario: str
    correo: str
    rol: str
    estado: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    correo: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: int
    rol: str
