from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # Evolution Cloud.ru API
    evolution_api_key: str
    evolution_base_url: str = "https://foundation-models.api.internal.cloud.ru/v1"
    
    @field_validator('evolution_base_url', mode='after')
    @classmethod
    def clean_base_url(cls, v: str) -> str:
        """Clean up base_url if it contains the variable name prefix (common .env mistake)"""
        if not v:
            return v
        # If the value contains "EVOLUTION_BASE_URL=", extract the URL after the last "="
        if "EVOLUTION_BASE_URL=" in v:
            # Find the last occurrence of "=" and take everything after it
            last_eq_index = v.rfind("=")
            if last_eq_index >= 0 and last_eq_index < len(v) - 1:
                cleaned = v[last_eq_index + 1:].strip()
                # Verify it's a valid URL
                if cleaned.startswith(('http://', 'https://')):
                    return cleaned
        # If it doesn't start with http, try to fix it
        if not v.startswith(('http://', 'https://')):
            # Try to extract URL from malformed value
            if "=" in v:
                parts = v.split("=")
                for part in reversed(parts):
                    part = part.strip()
                    if part.startswith(('http://', 'https://')):
                        return part
        return v.strip()
    
    # Database
    database_url: str
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    upload_dir: str = "/app/volumes/audio"
    transcripts_dir: str = "/app/volumes/transcripts"
    logs_dir: str = "/app/volumes/logs"
    max_file_size_mb: int = 25
    keep_original_files: bool = False
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def model_post_init(self, __context):
        """Post-initialization hook to clean up base_url"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"model_post_init called, base_url: {repr(self.evolution_base_url)}")
        if self.evolution_base_url and "EVOLUTION_BASE_URL=" in self.evolution_base_url:
            # Extract URL after the last "="
            last_eq_index = self.evolution_base_url.rfind("=")
            if last_eq_index >= 0:
                cleaned = self.evolution_base_url[last_eq_index + 1:].strip()
                logger.info(f"Cleaned URL: {repr(cleaned)}")
                if cleaned.startswith(('http://', 'https://')):
                    # Use object.__setattr__ to bypass pydantic's immutability
                    object.__setattr__(self, 'evolution_base_url', cleaned)
                    logger.info(f"Updated base_url to: {repr(self.evolution_base_url)}")


settings = Settings()

