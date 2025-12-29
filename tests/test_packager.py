"""
CiteKit – Packager Tests
Unit tests for package generation functionality
"""

import pytest
import json
import zipfile
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from packager import Packager
from models import MCPOutput, MCPEndpoint, MCPPriority, SitemapOutput, SitemapEntry


class TestPackager:
    """Tests for Packager class."""

    @pytest.fixture
    def packager(self):
        """Create a Packager instance with temp output dir."""
        with patch('packager.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(output_dir=tempfile.mkdtemp())
            return Packager()

    # ============================================
    # SITEMAP GENERATION TESTS
    # ============================================

    def test_generate_sitemap(self, packager, sample_pages):
        """Test sitemap generation from pages."""
        sitemap = packager.generate_sitemap("example.com", sample_pages)
        
        assert sitemap.site == "example.com"
        assert len(sitemap.urls) == len(sample_pages)
        
        # Check that page types are correctly assigned
        page_types = [entry.page_type for entry in sitemap.urls]
        assert "homepage" in page_types

    def test_generate_sitemap_empty_pages(self, packager):
        """Test sitemap generation with no pages."""
        sitemap = packager.generate_sitemap("example.com", [])
        assert sitemap.site == "example.com"
        assert len(sitemap.urls) == 0

    # ============================================
    # DEPLOY GUIDE GENERATION TESTS
    # ============================================

    def test_generate_deploy_guide_contains_domain(self, packager):
        """Test that deploy guide contains the domain."""
        guide = packager.generate_deploy_guide("example.com", 10)
        
        assert "example.com" in guide
        assert "10" in guide  # Page count

    def test_generate_deploy_guide_has_required_sections(self, packager):
        """Test that deploy guide has all required sections."""
        guide = packager.generate_deploy_guide("example.com", 25)
        
        # Check for required sections
        assert "Quick Start" in guide or "robots.txt" in guide
        assert "llm.txt" in guide.lower()
        assert "Verification" in guide or "verify" in guide.lower()

    # ============================================
    # PAGE JSON PREPARATION TESTS
    # ============================================

    def test_prepare_page_json(self, packager, sample_page_data):
        """Test page JSON preparation."""
        result = packager.prepare_page_json(sample_page_data)
        
        assert result["url"] == sample_page_data.url
        assert result["title"] == sample_page_data.title
        assert result["description"] == sample_page_data.description
        assert result["content"] == sample_page_data.content
        assert "classification" in result

    def test_prepare_page_json_classification_structure(self, packager, sample_page_data):
        """Test that classification is properly structured."""
        result = packager.prepare_page_json(sample_page_data)
        
        assert "page_type" in result["classification"]
        assert "intent" in result["classification"]

    # ============================================
    # VALIDATION TESTS
    # ============================================

    def test_validate_artifacts_valid(self, packager, sample_pages, sample_mcp_output):
        """Test validation with valid artifacts."""
        llm_txt = "# EXAMPLE.COM\n\n" + "Content " * 20
        sitemap = SitemapOutput(
            site="example.com",
            urls=[SitemapEntry(url="https://example.com", page_type="homepage")]
        )
        
        errors = packager.validate_artifacts(llm_txt, sample_mcp_output, sitemap, sample_pages)
        assert errors == []

    def test_validate_artifacts_empty_llm_txt(self, packager, sample_pages, sample_mcp_output):
        """Test validation catches empty llm.txt."""
        sitemap = SitemapOutput(
            site="example.com",
            urls=[SitemapEntry(url="https://example.com", page_type="homepage")]
        )
        
        errors = packager.validate_artifacts("", sample_mcp_output, sitemap, sample_pages)
        assert any("llm.txt" in e.lower() for e in errors)

    def test_validate_artifacts_no_endpoints(self, packager, sample_pages):
        """Test validation catches MCP with no endpoints."""
        llm_txt = "# Test\n" + "Content " * 20
        mcp = MCPOutput(site="example.com", endpoints=[])
        sitemap = SitemapOutput(
            site="example.com",
            urls=[SitemapEntry(url="https://example.com", page_type="homepage")]
        )
        
        errors = packager.validate_artifacts(llm_txt, mcp, sitemap, sample_pages)
        assert any("endpoint" in e.lower() for e in errors)

    def test_validate_artifacts_no_pages(self, packager, sample_mcp_output):
        """Test validation catches empty pages list."""
        llm_txt = "# Test\n" + "Content " * 20
        sitemap = SitemapOutput(
            site="example.com",
            urls=[SitemapEntry(url="https://example.com", page_type="homepage")]
        )
        
        errors = packager.validate_artifacts(llm_txt, sample_mcp_output, sitemap, [])
        assert any("pages" in e.lower() for e in errors)

    # ============================================
    # ROBOTS.TXT GENERATION TESTS
    # ============================================

    def test_generate_robots_txt(self, packager):
        """Test robots.txt generation."""
        robots = packager._generate_robots_txt("example.com")
        
        # Check for essential AI crawler entries
        assert "GPTBot" in robots
        assert "ClaudeBot" in robots
        assert "User-agent:" in robots
        assert "Allow: /" in robots

    def test_generate_robots_txt_contains_sitemap(self, packager):
        """Test that robots.txt contains sitemap reference."""
        robots = packager._generate_robots_txt("example.com")
        assert "Sitemap:" in robots


class TestPackagerZipCreation:
    """Tests for ZIP file creation."""

    @pytest.fixture
    def packager(self):
        """Create a Packager instance with temp output dir."""
        with patch('packager.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(output_dir=tempfile.mkdtemp())
            p = Packager()
            return p

    def test_create_zip_returns_path(self, packager, sample_pages, sample_mcp_output):
        """Test that create_zip returns a valid path."""
        llm_txt = "# TEST\n\nTest content here."
        sitemap = SitemapOutput(
            site="example.com",
            urls=[SitemapEntry(url="https://example.com", page_type="homepage")]
        )
        
        with patch.object(packager, '_generate_schema_files', return_value={}):
            zip_path = packager.create_zip(
                domain="example.com",
                llm_txt=llm_txt,
                mcp=sample_mcp_output,
                sitemap=sitemap,
                pages=sample_pages
            )
        
        assert zip_path is not None
        assert zip_path.endswith(".zip")
        assert Path(zip_path).exists()

    def test_create_zip_contains_required_files(self, packager, sample_pages, sample_mcp_output):
        """Test that ZIP contains all required files."""
        llm_txt = "# TEST\n\nTest content here."
        sitemap = SitemapOutput(
            site="example.com",
            urls=[SitemapEntry(url="https://example.com", page_type="homepage")]
        )
        
        with patch.object(packager, '_generate_schema_files', return_value={"test-schema.html": "<html></html>"}):
            zip_path = packager.create_zip(
                domain="example.com",
                llm_txt=llm_txt,
                mcp=sample_mcp_output,
                sitemap=sitemap,
                pages=sample_pages
            )
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            
            # Check required files
            assert "llm.txt" in names
            assert "robots.txt" in names
            assert "sitemap.json" in names
            assert "index.html" in names
            assert "DEPLOYMENT-GUIDE.md" in names
            
            # Check pages directory
            page_files = [n for n in names if n.startswith("pages/")]
            assert len(page_files) > 0

    def test_create_zip_deterministic_naming(self, packager, sample_pages, sample_mcp_output):
        """Test that ZIP filename is deterministic."""
        llm_txt = "# TEST\n\nTest content."
        sitemap = SitemapOutput(site="example.com", urls=[])
        
        with patch.object(packager, '_generate_schema_files', return_value={}):
            zip_path = packager.create_zip(
                domain="example.com",
                llm_txt=llm_txt,
                mcp=sample_mcp_output,
                sitemap=sitemap,
                pages=sample_pages
            )
        
        assert "example_com" in zip_path
        assert "-geo.zip" in zip_path
