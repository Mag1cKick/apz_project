from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_port: int  # defined in .env, no default
    postgres_url: str
    redis_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 60

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()