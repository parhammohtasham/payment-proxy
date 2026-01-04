"""
Configuration settings for Payment Proxy
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Zibal Configuration
    ZIBAL_MERCHANT_ID: str = "zibal"
    ZIBAL_VERIFY_URL: str = "https://gateway.zibal.ir/v1/verify"
    ZIBAL_PAYMENT_URL: str = "https://gateway.zibal.ir/start/"
    
    # Ticketing API
    TICKETING_API_URL: str
    TICKETING_FRONTEND_URL: str
    
    # Security
    WEBHOOK_SECRET: str
    
    # Optional
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
