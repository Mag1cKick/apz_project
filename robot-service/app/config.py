from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_port: int  # defined in .env, no default
    mongo_uri: str
    mongo_db: str
    jwt_secret: str

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()