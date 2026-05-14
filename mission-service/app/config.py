from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_port: int  # defined in .env, no default
    postgres_url: str
    jwt_secret: str

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()