"""
CiteKit – Configuration
Cloud Run & Local Development Compatible
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra env vars that aren't defined
    )
    
    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    llm_temperature: float = 0.2

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: Optional[str] = None  # Admin key for bypassing RLS

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Razorpay Payment Gateway
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    
    # Pricing Configuration
    payment_amount_paise: int = 90000
    payment_currency: str = "INR"
    
    # Security
    jwt_secret: str = "dev-secret-change-in-production"
    
    # Admin email (for admin panel access)
    admin_email: str = ""

    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:5173"
    
    # CORS - Comma-separated list of allowed origins
    allowed_origins: str = ""

    # Crawl settings
    max_pages: int = 50
    request_timeout: int = 30
    concurrent_requests: int = 5
    
    # LLM cost optimization
    classification_batch_size: int = 5
    max_content_tokens: int = 1500
    
    # Output directory
    output_dir: str = ""
    
    # Mailgun Email
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    email_from: str = ""
    mailgun_api_base: str = "https://api.mailgun.net/v3"
    
    # Cloud Run Detection
    @property
    def is_cloud_run(self) -> bool:
        return os.environ.get("K_SERVICE") is not None
    
    @property
    def is_production(self) -> bool:
        return self.is_cloud_run or os.environ.get("ENV", "").lower() == "production"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get list of allowed CORS origins"""
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "https://wantaiseo.com",
            "https://www.wantaiseo.com",
        ]
        
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        
        if self.allowed_origins:
            custom_origins = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
            origins.extend(custom_origins)
        
        return list(set(origins))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.output_dir or self.output_dir == "./output":
            from pathlib import Path
            if os.environ.get("K_SERVICE"):
                self.output_dir = "/app/output"
            else:
                project_root = Path(__file__).parent.parent
                self.output_dir = str(project_root / "output")

_settings = None
def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings