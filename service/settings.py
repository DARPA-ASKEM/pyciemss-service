"""
Configures pyciemss-service using environment variables
"""
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    pyciemss-service configuration
    """
    TDS_URL: str = "http://data-service-api:8000"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    RABBITMQ_HOST: str = "rabbitmq.pyciemss"
    RABBITMQ_PORT: int = 5672


settings = Settings()
