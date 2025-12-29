"""
CiteKit – Content Extractor
Static + headless fetching with content extraction
Per FR-2: Content Extraction
"""

import asyncio
import json
import re
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
import trafilatura
from playwright.async_api import async_playwright

from config import get_settings
from models import PageData

# Configure logging
logger = logging.getLogger("geo-compiler.extractor")


class ContentExtractor:
    """
    Content extraction pipeline.
    Static fetch first, headless fallback for JS-heavy pages.
    """

    def __init__(self):
        self.settings = get_settings()

    # ============================================
    # STATIC FETCHING
    # ============================================

    async def fetch_static(self, url: str) -> Optional[str]:
        """
        Fetch page content using httpx (static).
        Retries with SSL verification disabled if initial attempt fails.
        """
        # First attempt with SSL verification
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
        except httpx.HTTPStatusError as e:
            print(f"   ⚠️ HTTP error for {url}: {e.response.status_code}")
        except Exception as e:
            # Check if it's an SSL error
            error_str = str(e).lower()
            if "ssl" in error_str or "certificate" in error_str:
                print(f"   ⚠️ SSL error for {url}, retrying without verification...")
                # Retry without SSL verification
                try:
                    async with httpx.AsyncClient(
                        timeout=self.settings.request_timeout,
                        follow_redirects=True,
                        verify=False  # Disable SSL verification
                    ) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            print(f"   ✅ Successfully fetched {url} (SSL verify disabled)")
                            return response.text
                except Exception as retry_error:
                    print(f"   ❌ Retry also failed for {url}: {retry_error}")
            else:
                print(f"   ⚠️ Fetch error for {url}: {e}")
        return None

    # ============================================
    # HEADLESS FETCHING (Playwright)
    # ============================================

    async def fetch_headless(self, url: str) -> Optional[str]:
        """
        Fetch page content using Playwright (headless Chromium).
        Used as fallback for JS-rendered pages.
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle", timeout=30000)
                content = await page.content()

                await browser.close()
                return content
        except Exception:
            pass
        return None

    # ============================================
    # CONTENT EXTRACTION
    # ============================================

    def extract_content(self, html: str, url: str) -> str:
        """
        Extract main readable content using Trafilatura.
        Removes navigation, footer, ads, cookies.
        """
        try:
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
                url=url
            )
            return content or ""
        except Exception:
            return ""

    # ============================================
    # METADATA EXTRACTION
    # ============================================

    def extract_metadata(self, html: str) -> dict:
        """
        Extract metadata: title, description, headings, JSON-LD.
        """
        metadata = {
            "title": "",
            "description": "",
            "headings": [],
            "json_ld": None
        }

        try:
            soup = BeautifulSoup(html, "lxml")

            # Title
            title_tag = soup.find("title")
            if title_tag:
                metadata["title"] = title_tag.get_text(strip=True)

            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                metadata["description"] = meta_desc["content"]

            # OG description fallback
            if not metadata["description"]:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    metadata["description"] = og_desc["content"]

            # Headings (h1-h3)
            for level in ["h1", "h2", "h3"]:
                for heading in soup.find_all(level):
                    text = heading.get_text(strip=True)
                    if text:
                        metadata["headings"].append(text)

            # JSON-LD structured data
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    metadata["json_ld"] = data
                    break  # Take first valid JSON-LD
                except (json.JSONDecodeError, TypeError):
                    pass

        except Exception:
            pass

        return metadata

    # ============================================
    # DETECT JS-HEAVY PAGES
    # ============================================

    def _needs_js_rendering(self, html: str) -> bool:
        """
        Detect if page likely needs JavaScript rendering.
        """
        soup = BeautifulSoup(html, "lxml")

        # Check for common SPA indicators
        body = soup.find("body")
        if body:
            body_text = body.get_text(strip=True)
            # Very little text content suggests JS rendering needed
            if len(body_text) < 100:
                return True

        # Check for React/Vue/Angular root divs
        spa_indicators = ["#app", "#root", "#__next", "[data-reactroot]"]
        for indicator in spa_indicators:
            if soup.select(indicator):
                # Check if div is mostly empty
                elem = soup.select_one(indicator)
                if elem and len(elem.get_text(strip=True)) < 50:
                    return True

        return False

    # ============================================
    # PROCESS PAGE
    # ============================================

    async def process_page(self, url: str) -> Optional[PageData]:
        """
        Unified page processing: fetch, extract, return PageData.
        """
        # 1. Try static fetch first
        html = await self.fetch_static(url)

        # 2. Check if JS rendering needed
        if html and self._needs_js_rendering(html):
            html_js = await self.fetch_headless(url)
            if html_js:
                html = html_js

        if not html:
            return None

        # 3. Extract metadata
        metadata = self.extract_metadata(html)

        # 4. Extract main content
        content = self.extract_content(html, url)

        # 5. Skip pages with no content
        if not content and not metadata["title"]:
            return None

        # 6. Build PageData
        return PageData(
            url=url,
            title=metadata["title"],
            description=metadata["description"],
            content=content or "",
            headings=metadata["headings"],
            classification={}  # Filled by classifier
        )

    # ============================================
    # URL SLUG GENERATION
    # ============================================

    @staticmethod
    def url_to_slug(url: str) -> str:
        """Convert URL to safe filename slug."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return "homepage"

        # Replace slashes and special chars
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", path)
        slug = slug.strip("_").lower()

        return slug[:100] if slug else "page"
