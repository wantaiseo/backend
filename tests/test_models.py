"""
CiteKit – Model Tests
Unit tests for Pydantic models and validation
"""

import pytest
from datetime import datetime

from models import (
    CompileRequest,
    CrawlDepth,
    PageData,
    PageClassification,
    MCPOutput,
    MCPEndpoint,
    MCPPriority,
    CompileJob,
    JobStatus,
    SitemapOutput,
    SitemapEntry,
    CompileResponse,
    JobStatusResponse
)


class TestCompileRequest:
    """Tests for CompileRequest model."""

    def test_valid_url_with_https(self):
        """Test that valid HTTPS URL is accepted."""
        request = CompileRequest(url="https://example.com")
        assert request.url == "https://example.com"

    def test_url_without_scheme_adds_https(self):
        """Test that URL without scheme gets https:// prepended."""
        request = CompileRequest(url="example.com")
        assert request.url == "https://example.com"

    def test_url_with_http_preserved(self):
        """Test that http:// URLs are preserved."""
        request = CompileRequest(url="http://example.com")
        assert request.url == "http://example.com"

    def test_url_with_whitespace_stripped(self):
        """Test that whitespace is stripped from URL."""
        request = CompileRequest(url="  https://example.com  ")
        assert request.url == "https://example.com"

    def test_default_crawl_depth_is_auto(self):
        """Test that default crawl depth is AUTO."""
        request = CompileRequest(url="https://example.com")
        assert request.crawl_depth == CrawlDepth.AUTO

    def test_custom_crawl_depth(self):
        """Test setting custom crawl depth."""
        request = CompileRequest(url="https://example.com", crawl_depth=CrawlDepth.DEEP)
        assert request.crawl_depth == CrawlDepth.DEEP

    def test_include_subdomains_default_false(self):
        """Test that include_subdomains defaults to False."""
        request = CompileRequest(url="https://example.com")
        assert request.include_subdomains is False

    def test_competitors_empty_by_default(self):
        """Test that competitors list is empty by default."""
        request = CompileRequest(url="https://example.com")
        assert request.competitors == []


class TestPageData:
    """Tests for PageData model."""

    def test_valid_page_data(self, sample_page_data):
        """Test creating valid PageData."""
        assert sample_page_data.url == "https://example.com/about"
        assert "Example Company" in sample_page_data.title
        assert len(sample_page_data.headings) == 3

    def test_page_data_with_empty_content(self):
        """Test PageData with empty content is valid."""
        page = PageData(
            url="https://example.com/empty",
            title="Empty Page",
            description="",
            content=""
        )
        assert page.content == ""

    def test_page_data_classification_default_empty(self):
        """Test that classification defaults to empty dict."""
        page = PageData(
            url="https://example.com",
            title="Test",
            description="Test desc",
            content="Test content"
        )
        assert page.classification == {}


class TestMCPOutput:
    """Tests for MCP-related models."""

    def test_mcp_endpoint_priorities(self):
        """Test all priority levels are valid."""
        for priority in [MCPPriority.LOW, MCPPriority.MEDIUM, MCPPriority.HIGH, MCPPriority.CRITICAL]:
            endpoint = MCPEndpoint(
                url="https://example.com",
                description="Test",
                use_when="Test case",
                topics=["test"],
                priority=priority
            )
            assert endpoint.priority == priority

    def test_mcp_output_with_endpoints(self, sample_mcp_output):
        """Test MCPOutput with endpoints."""
        assert sample_mcp_output.site == "example.com"
        assert len(sample_mcp_output.endpoints) == 2
        assert sample_mcp_output.version == "1.0"

    def test_mcp_output_generated_at_set_automatically(self):
        """Test that generated_at is set automatically."""
        mcp = MCPOutput(site="example.com", endpoints=[])
        assert mcp.generated_at is not None


class TestJobStatus:
    """Tests for JobStatus enum and CompileJob model."""

    def test_all_job_statuses_exist(self):
        """Test all required job statuses exist."""
        required_statuses = [
            "pending", "discovering", "crawling", "extracting",
            "classifying", "synthesizing", "packaging", "completed",
            "failed", "cancelled"
        ]
        for status in required_statuses:
            assert hasattr(JobStatus, status.upper())

    def test_compile_job_defaults(self, sample_job):
        """Test CompileJob default values."""
        assert sample_job.status == JobStatus.PENDING
        assert sample_job.progress == 0
        assert sample_job.error is None
        assert sample_job.result_path is None

    def test_compile_job_created_at_set_automatically(self):
        """Test that created_at is set automatically."""
        job = CompileJob(job_id="test", url="https://example.com")
        assert job.created_at is not None


class TestSitemapOutput:
    """Tests for sitemap models."""

    def test_sitemap_entry(self):
        """Test SitemapEntry creation."""
        entry = SitemapEntry(url="https://example.com", page_type="homepage")
        assert entry.url == "https://example.com"
        assert entry.page_type == "homepage"

    def test_sitemap_output_with_entries(self):
        """Test SitemapOutput with multiple entries."""
        sitemap = SitemapOutput(
            site="example.com",
            urls=[
                SitemapEntry(url="https://example.com", page_type="homepage"),
                SitemapEntry(url="https://example.com/about", page_type="about"),
            ]
        )
        assert len(sitemap.urls) == 2


class TestAPIResponses:
    """Tests for API response models."""

    def test_compile_response(self):
        """Test CompileResponse creation."""
        response = CompileResponse(
            job_id="test-123",
            status=JobStatus.PENDING,
            message="Job started"
        )
        assert response.job_id == "test-123"
        assert response.status == JobStatus.PENDING

    def test_job_status_response(self):
        """Test JobStatusResponse creation."""
        response = JobStatusResponse(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            progress=100,
            total_pages=25,
            geo_score=85
        )
        assert response.progress == 100
        assert response.geo_score == 85
