from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    service_port: int = 8003
    postgres_url: str = "postgresql+asyncpg://mission_user:mission_pass@mission-db:5432/mission_db"
    hazelcast_members: str = "hazelcast1:5701,hazelcast2:5701,hazelcast3:5701"
    hazelcast_cluster_name: str = "robotops-hz"
    jwt_secret: str = "robotops-secret-change-me"

    model_config = {"env_file": ".env", "case_sensitive": False}

    def hazelcast_member_list(self) -> List[str]:
        return [m.strip() for m in self.hazelcast_members.split(",")]


settings = Settings()
