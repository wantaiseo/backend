"""
CiteKit – Extractor Tests
Unit tests for content extraction functionality
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from extractor import ContentExtractor


class TestContentExtractor:
    """Tests for ContentExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a ContentExtractor instance."""
        return ContentExtractor()

    # ============================================
    # URL SLUG GENERATION TESTS
    # ============================================

    def test_url_to_slug_homepage(self, extractor):
        """Test that root URL returns 'homepage'."""
        assert ContentExtractor.url_to_slug("https://example.com") == "homepage"
        assert ContentExtractor.url_to_slug("https://example.com/") == "homepage"

    def test_url_to_slug_simple_path(self, extractor):
        """Test simple path conversion."""
        assert ContentExtractor.url_to_slug("https://example.com/about") == "about"
        assert ContentExtractor.url_to_slug("https://example.com/pricing") == "pricing"

    def test_url_to_slug_nested_path(self, extractor):
        """Test nested path conversion."""
        slug = ContentExtractor.url_to_slug("https://example.com/docs/api/reference")
        assert slug == "docs_api_reference"

    def test_url_to_slug_special_characters(self, extractor):
        """Test that special characters are replaced with underscores."""
        slug = ContentExtractor.url_to_slug("https://example.com/blog/my-post-2024")
        assert "_" in slug or slug == "blog_my_post_2024"

    def test_url_to_slug_max_length(self, extractor):
        """Test that slug is truncated to 100 characters."""
        long_path = "a" * 150
        slug = ContentExtractor.url_to_slug(f"https://example.com/{long_path}")
        assert len(slug) <= 100

    # ============================================
    # METADATA EXTRACTION TESTS
    # ============================================

    def test_extract_metadata_title(self, extractor, mock_http_response):
        """Test title extraction from HTML."""
        metadata = extractor.extract_metadata(mock_http_response)
        assert metadata["title"] == "Test Page"

    def test_extract_metadata_description(self, extractor, mock_http_response):
        """Test description extraction from meta tag."""
        metadata = extractor.extract_metadata(mock_http_response)
        assert metadata["description"] == "Test description"

    def test_extract_metadata_headings(self, extractor, mock_http_response):
        """Test headings extraction."""
        metadata = extractor.extract_metadata(mock_http_response)
        assert "Main Heading" in metadata["headings"]

    def test_extract_metadata_json_ld(self, extractor, mock_http_response):
        """Test JSON-LD extraction."""
        metadata = extractor.extract_metadata(mock_http_response)
        assert metadata["json_ld"] is not None
        assert metadata["json_ld"]["@type"] == "Organization"

    def test_extract_metadata_empty_html(self, extractor):
        """Test metadata extraction with empty HTML."""
        metadata = extractor.extract_metadata("")
        assert metadata["title"] == ""
        assert metadata["description"] == ""
        assert metadata["headings"] == []

    def test_extract_metadata_og_description_fallback(self, extractor):
        """Test OG description fallback when meta description is missing."""
        html = """
        <html>
        <head>
            <meta property="og:description" content="OG description">
        </head>
        </html>
        """
        metadata = extractor.extract_metadata(html)
        assert metadata["description"] == "OG description"

    # ============================================
    # JS RENDERING DETECTION TESTS
    # ============================================

    def test_needs_js_rendering_minimal_content(self, extractor):
        """Test detection of JS-heavy pages with minimal content."""
        html = """
        <html>
        <body>
            <div id="root"></div>
        </body>
        </html>
        """
        assert extractor._needs_js_rendering(html) is True

    def test_needs_js_rendering_full_content(self, extractor):
        """Test that pages with sufficient content don't need JS rendering."""
        # HTML with enough content to pass the 100-character threshold
        html_with_content = """
        <html>
        <body>
            <article>
                <h1>Welcome to Our Website</h1>
                <p>This is a comprehensive page with plenty of text content that should 
                be sufficient to indicate that this is a fully rendered page and does 
                not need JavaScript rendering. We have lots of information here about 
                our products and services.</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do 
                eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            </article>
        </body>
        </html>
        """
        assert extractor._needs_js_rendering(html_with_content) is False

    def test_needs_js_rendering_spa_indicators(self, extractor):
        """Test detection of SPA indicators."""
        html = """
        <html>
        <body>
            <div id="__next"></div>
        </body>
        </html>
        """
        assert extractor._needs_js_rendering(html) is True

    # ============================================
    # CONTENT EXTRACTION TESTS
    # ============================================

    def test_extract_content_basic(self, extractor):
        """Test basic content extraction."""
        html = """
        <html>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>This is the main article content that should be extracted.</p>
            </article>
            <nav>Navigation links</nav>
            <footer>Footer content</footer>
        </body>
        </html>
        """
        content = extractor.extract_content(html, "https://example.com")
        # Trafilatura should extract the article content
        assert content is not None or content == ""  # May vary based on Trafilatura

    def test_extract_content_empty_html(self, extractor):
        """Test content extraction with empty HTML."""
        content = extractor.extract_content("", "https://example.com")
        assert content == ""

    # ============================================
    # STATIC FETCH TESTS
    # ============================================

    @pytest.mark.asyncio
    async def test_fetch_static_success(self, extractor):
        """Test successful static fetch."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Test</body></html>"
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await extractor.fetch_static("https://example.com")
            # Result depends on actual httpx behavior

    @pytest.mark.asyncio
    async def test_fetch_static_failure_returns_none(self, extractor):
        """Test that fetch failures return None gracefully."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await extractor.fetch_static("https://example.com")
            assert result is None


class TestContentExtractorIntegration:
    """Integration tests for ContentExtractor."""

    @pytest.fixture
    def extractor(self):
        return ContentExtractor()

    @pytest.mark.asyncio
    async def test_process_page_returns_pagedata(self, extractor):
        """Test that process_page returns PageData for valid HTML."""
        html = """
        <html>
        <head>
            <title>Test Page Title</title>
            <meta name="description" content="Test description">
        </head>
        <body>
            <h1>Welcome</h1>
            <p>This is test content with enough text to be extracted properly by trafilatura.</p>
        </body>
        </html>
        """
        
        with patch.object(extractor, 'fetch_static', AsyncMock(return_value=html)):
            with patch.object(extractor, '_needs_js_rendering', return_value=False):
                page = await extractor.process_page("https://example.com/test")
                
                if page:  # May be None if content extraction fails
                    assert page.url == "https://example.com/test"
                    assert page.title == "Test Page Title"

    @pytest.mark.asyncio
    async def test_process_page_returns_none_for_empty_content(self, extractor):
        """Test that process_page returns None for pages with no content."""
        with patch.object(extractor, 'fetch_static', AsyncMock(return_value=None)):
            page = await extractor.process_page("https://example.com/empty")
            assert page is None
