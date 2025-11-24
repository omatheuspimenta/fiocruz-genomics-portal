from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, computed_field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Fiocruz Browser API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""
    
    # Elasticsearch
    ELASTICSEARCH_URL: str
    ES_INDEX: str
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    
    # Security (Example of a required secret)
    # If this is not set in .env or env vars, the app will fail to start.
    SECRET_KEY: str 

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
