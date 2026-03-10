from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "DevApply API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://devapply:devapply_pass@localhost:5432/devapply"
    
    # Security
    SECRET_KEY: str = "SUPER_SECRET_KEY_CHANGE_ME"  # Should be generated 256-bit random
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # AI / LLM
    GEMINI_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Email (SMTP or SendGrid)
    SMTP_HOST: str = "smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey"
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "agent@devapply.io"
    FROM_NAME: str = "DevApply AI Agent"
    
    # Tier Limits
    FREE_TIER_LIMIT: int = 2
    PRO_TIER_LIMIT: int = 10
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

TIER_DAILY_LIMITS = {
    "free": settings.FREE_TIER_LIMIT,
    "pro": settings.PRO_TIER_LIMIT,
    "max": None,  # Unlimited
}

def get_daily_limit(tier: str) -> Optional[int]:
    return TIER_DAILY_LIMITS.get(tier, settings.FREE_TIER_LIMIT)
