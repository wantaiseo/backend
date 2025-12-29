"""
CiteKit – Pydantic Models
All schemas defined per SCHEMAS.md specification
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl, Field, field_validator


# ============================================
# INPUT MODELS
# ============================================

class CrawlDepth(str, Enum):
    AUTO = "auto"
    SHALLOW = "shallow"
    DEEP = "deep"


class CompileRequest(BaseModel):
    """Input request for website compilation"""
    url: str
    crawl_depth: CrawlDepth = CrawlDepth.AUTO
    include_subdomains: bool = False
    competitors: list[str] = []
    payment_id: Optional[str] = None  # Razorpay Payment ID if paid


class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    DISCOVERING = "discovering"
    EXTRACTING = "extracting"
    CLASSIFYING = "classifying"
    SYNTHESIZING = "synthesizing"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageClassification(BaseModel):
    """Classification output for a page"""
    page_type: str = "other"
    primary_intent: str = "informational"
    confidence: float = 0.5


class PageData(BaseModel):
    """Extracted page data"""
    url: str
    title: str = ""
    description: str = ""
    content: str = ""
    headings: list[str] = []
    classification: dict = {}


class MCPPriority(str, Enum):
    """Priority levels for MCP endpoints"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MCPEndpoint(BaseModel):
    """Single MCP endpoint - enhanced for spec compliance"""
    url: str
    description: str
    priority: str = "medium"
    use_when: str = ""  # When should AI agents use this endpoint
    topics: list[str] = []  # Related topics for better matching
    content_type: str = "text/html"  # Expected content type


class MCPContact(BaseModel):
    """Contact information for the MCP file"""
    name: Optional[str] = None
    email: Optional[str] = None
    url: Optional[str] = None


class MCPOutput(BaseModel):
    """MCP JSON output - enhanced with full spec fields"""
    site: str
    name: str = ""  # Human-readable site name
    description: str = ""  # Brief site description
    version: str = "1.0"
    generated_at: str = ""  # ISO timestamp
    generator: str = "CiteKit"
    contact: Optional[MCPContact] = None
    llms_txt_url: str = ""  # URL to llms.txt file
    facts_jsonld_url: str = ""  # URL to facts.jsonld
    endpoints: list[MCPEndpoint] = []


class SitemapEntry(BaseModel):
    """Single sitemap entry"""
    url: str
    page_type: str = "other"


class SitemapOutput(BaseModel):
    """Sitemap JSON output"""
    site: str
    urls: list[SitemapEntry] = []


class CompileJob(BaseModel):
    """Job tracking model"""
    job_id: str
    url: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    total_pages: int = 0
    geo_score: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    downloaded_at: Optional[str] = None  # Track when user downloaded the package
    error: Optional[str] = None
    result_path: Optional[str] = None
    user_id: Optional[str] = None
    payment_id: Optional[str] = None  # Track associated payment
    output_data: Optional[dict] = None  # Stored preview data (audit, llm.txt) for instant access



# ============================================
# API RESPONSES
# ============================================

class CompileResponse(BaseModel):
    """Response when starting a compile job"""
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str
    status: JobStatus
    progress: int
    total_pages: int
    url: Optional[str] = None
    geo_score: Optional[int] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    is_paid: bool = False
    logs: list[str] = []  # Execution logs for frontend display

