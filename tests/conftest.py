"""
CiteKit – Test Fixtures
Shared pytest fixtures for all tests
"""

import pytest
import asyncio
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

from models import PageData, CompileJob, JobStatus, MCPOutput, MCPEndpoint, MCPPriority


# ============================================
# EVENT LOOP FIXTURE
# ============================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================
# SAMPLE DATA FIXTURES
# ============================================

@pytest.fixture
def sample_page_data() -> PageData:
    """Return a sample PageData object for testing."""
    return PageData(
        url="https://example.com/about",
        title="About Us - Example Company",
        description="Learn about Example Company and our mission.",
        content="Example Company is a leading provider of innovative solutions. Founded in 2010, we serve customers worldwide.",
        headings=["About Us", "Our Mission", "Our Team"],
        classification={
            "page_type": "about",
            "primary_intent": "informational",
            "topics": ["company", "about", "team"],
            "confidence": 0.95
        }
    )


@pytest.fixture
def sample_pages() -> list[PageData]:
    """Return a list of sample PageData objects for testing."""
    return [
        PageData(
            url="https://example.com",
            title="Example Company - Home",
            description="Welcome to Example Company",
            content="Welcome to our homepage. We offer the best products.",
            headings=["Welcome", "Our Products", "Contact"],
            classification={"page_type": "homepage", "primary_intent": "informational", "topics": ["home", "welcome"]}
        ),
        PageData(
            url="https://example.com/pricing",
            title="Pricing - Example Company",
            description="View our pricing plans",
            content="We offer three plans: Basic $10/mo, Pro $25/mo, Enterprise $100/mo.",
            headings=["Pricing", "Basic Plan", "Pro Plan", "Enterprise Plan"],
            classification={"page_type": "pricing", "primary_intent": "commercial", "topics": ["pricing", "plans"]}
        ),
        PageData(
            url="https://example.com/docs",
            title="Documentation - Example Company",
            description="API and product documentation",
            content="Getting started with our API. First, install the SDK...",
            headings=["Getting Started", "Installation", "API Reference"],
            classification={"page_type": "documentation", "primary_intent": "instructional", "topics": ["docs", "api"]}
        ),
    ]


@pytest.fixture
def sample_job() -> CompileJob:
    """Return a sample CompileJob for testing."""
    return CompileJob(
        job_id="test-job-123",
        url="https://example.com",
        status=JobStatus.PENDING,
        progress=0,
        total_pages=0
    )


@pytest.fixture
def sample_mcp_output() -> MCPOutput:
    """Return a sample MCPOutput for testing."""
    return MCPOutput(
        site="example.com",
        version="1.0",
        endpoints=[
            MCPEndpoint(
                url="https://example.com",
                description="Homepage",
                use_when="User asks about the company overview",
                topics=["home", "welcome"],
                priority=MCPPriority.CRITICAL
            ),
            MCPEndpoint(
                url="https://example.com/pricing",
                description="Pricing page",
                use_when="User asks about pricing or costs",
                topics=["pricing", "plans"],
                priority=MCPPriority.HIGH
            ),
        ]
    )


# ============================================
# MOCK FIXTURES
# ============================================

@pytest.fixture
def mock_database():
    """Return a mock database client."""
    mock = MagicMock()
    mock.create_job = AsyncMock(return_value=None)
    mock.get_job = AsyncMock(return_value=None)
    mock.update_job = AsyncMock(return_value=None)
    mock.update_job_status = AsyncMock(return_value=None)
    mock.save_page = AsyncMock(return_value=None)
    mock.save_discovered_urls = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_http_response():
    """Return mock HTTP response content."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is test content for extraction.</p>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Test Company"
        }
        </script>
    </body>
    </html>
    """
