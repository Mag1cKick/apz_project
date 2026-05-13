from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_port: int = 8002
    mongo_uri: str = "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0"
    mongo_db: str = "robot_db"
    jwt_secret: str = "robotops-secret-change-me"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
