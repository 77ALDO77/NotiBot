from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    DATABASE_URL: str = "postgresql+asyncpg://notibot:notibot@localhost:5432/notibot"
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost,http://localhost:4200"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
