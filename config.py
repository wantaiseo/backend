"""
CiteKit – Configuration
Cloud Run & Local Development Compatible
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    llm_temperature: float = 0.2  # Per NFR: ≤ 0.2 for determinism

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Razorpay Payment Gateway
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""  # From Razorpay Dashboard > Webhooks
    
    # Pricing Configuration
    # $10 USD ≈ ₹900 INR = 90000 paise (smallest unit)
    payment_amount_paise: int = 90000  # Amount in smallest currency unit
    payment_currency: str = "INR"  # INR for India, USD for international
    
    # Free Tier Configuration
    free_audit_limit: int = 2  # Number of free audits before payment required
    
    # Frontend URL (for OAuth redirects and CORS)
    frontend_url: str = "http://localhost:5173"
    
    # CORS - Comma-separated list of allowed origins (for production)
    # Example: "https://myapp.com,https://www.myapp.com"
    allowed_origins: str = ""
    
    # Email Configuration (Mailgun)
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    email_from: str = ""
    
    # Admin email (for admin panel access)
    admin_email: str = "samaypatel0402@gmail.com"

    # Crawl settings (cost-optimized defaults)
    max_pages: int = 50  # Reduced from 100 for $5 profitability
    request_timeout: int = 30
    concurrent_requests: int = 5
    
    # LLM cost optimization
    classification_batch_size: int = 5  # Batch pages per API call
    max_content_tokens: int = 1500  # Truncate content to save tokens

    # Output - use absolute path relative to project root
    output_dir: str = ""
    
    # Cloud Run Detection
    @property
    def is_cloud_run(self) -> bool:
        """Detect if running on Cloud Run"""
        return os.environ.get("K_SERVICE") is not None
    
    @property
    def is_production(self) -> bool:
        """Detect if running in production"""
        return self.is_cloud_run or os.environ.get("ENV", "").lower() == "production"
    
    @property
    def cors_origins(self) -> List[str]:
        """Get list of allowed CORS origins"""
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ]
        
        # Add frontend URL if set
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        
        # Add custom allowed origins
        if self.allowed_origins:
            custom_origins = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
            origins.extend(custom_origins)
        
        return list(set(origins))  # Remove duplicates
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Calculate absolute path: backend/config.py -> .. -> project_root/output
        if not self.output_dir or self.output_dir == "./output":
            from pathlib import Path
            # On Cloud Run, use /app/output
            if os.environ.get("K_SERVICE"):
                self.output_dir = "/app/output"
            else:
                project_root = Path(__file__).parent.parent
                self.output_dir = str(project_root / "output")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
