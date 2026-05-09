from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_port: int = 8001
    postgres_url: str = "postgresql+asyncpg://auth_user:auth_pass@auth-db:5432/auth_db"
    redis_url: str = "redis://redis:6379"
    jwt_secret: str = "robotops-secret-change-me"
    jwt_expire_minutes: int = 60

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
