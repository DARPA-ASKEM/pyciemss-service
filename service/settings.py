"""
Configures pyciemss-service using environment variables
"""

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    pyciemss-service configuration
    """

    TDS_URL: str = "http://data-service-api:8000"
    TDS_USER: str = "user"
    TDS_PASSWORD: str = "password"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    RABBITMQ_HOST: str = "rabbitmq.pyciemss"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"


settings = Settings()
