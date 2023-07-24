"""
Configures pyciemss-service using environment variables
"""
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    pyciemss-service configuration
    """
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    TDS_URL: str = "http://data-service-api:8000"
    PYCIEMSS_OUTPUT_FILEPATH: str = "result.csv"
    EVAL_OUTPUT_FILENAME: str = "eval.csv"


settings = Settings()
