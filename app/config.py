import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # MCP
    mcp_token: str = os.getenv("MCP_TOKEN", "change-me-in-production")
    
    # SiliconFlow
    siliconflow_api_key: str = os.getenv("SILICONFLOW_API_KEY", "")
    siliconflow_base_url: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    siliconflow_embedding_model: str = os.getenv("SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3")
    
    # Database
    database_path: str = os.getenv("DATABASE_PATH", "./memory.db")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
