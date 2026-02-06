"""
Configuration management for AI Operations Assistant.
Loads environment variables and provides centralized config access.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-3.5-turbo", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    
    # GitHub Configuration
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    github_api_base: str = "https://api.github.com"
    
    # OpenWeatherMap Configuration
    openweathermap_api_key: str = Field(default="", env="OPENWEATHERMAP_API_KEY")
    openweathermap_api_base: str = "https://api.openweathermap.org/data/2.5"
    
    # Application Configuration
    max_retries: int = 3
    request_timeout: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def validate_settings() -> dict:
    """Validate required settings and return status."""
    status = {
        "openai_configured": bool(settings.openai_api_key),
        "github_configured": bool(settings.github_token),
        "weather_configured": bool(settings.openweathermap_api_key),
    }
    status["all_required_configured"] = (
        status["openai_configured"] and status["weather_configured"]
    )
    return status
