"""
CiteKit – Discovery Engine
URL discovery via robots.txt, sitemap, and HTML crawling
Per FR-1: Website Discovery
"""

import asyncio
import re
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Optional
import httpx
from lxml import etree
from bs4 import BeautifulSoup
from config import get_settings

# Configure logging
logger = logging.getLogger("geo-compiler.discovery")


class DiscoveryEngine:
    """
    Discovery engine for website URL extraction.
    Handles robots.txt, sitemap.xml, and HTML link crawling.
    """

    def __init__(self, base_url: str, include_subdomains: bool = False):
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(base_url)
        self.domain = parsed.netloc
        self.scheme = parsed.scheme
        self.include_subdomains = include_subdomains
        self.discovered_urls: set[str] = set()
        self.disallowed_paths: list[str] = []
        self.settings = get_settings()
        
        # SSRF Protection: Validate base URL immediately
        if not self._is_safe_url(self.base_url):
            raise ValueError(f"CRITICAL SECURITY: {self.base_url} resolves to a restricted internal network address.")

    def _is_safe_url(self, url: str) -> bool:
        """
        SSRF Protection: Validate that a URL does NOT resolve to a private/internal IP.
        Blocks: localhost, 127.x, 192.168.x, 10.x, 172.16.x, 169.254.x (AWS metadata)
        """
        try:
            import socket
            import ipaddress
            
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
                
            # Allow common public domains immediately to save DNS lookup time
            # (Optional optimization, but we'll stick to safety first)
            
            # Resolve IP (handles DNS Rebinding attack by checking immediately before use, 
            # though TOCTOU still exists without specialized HTTP clients)
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
                
            # Double check for 0.0.0.0
            if str(ip) == "0.0.0.0":
                return False
                
            return True
        except Exception:
            # If we can't verify it, we should block it to be safe
            return False

    # ============================================
    # ROBOTS.TXT PARSING
    # ============================================

    async def parse_robots_txt(self) -> dict:
        """
        Parse robots.txt for crawl directives.
        Returns dict with sitemaps and disallowed paths.
        """
        robots_url = f"{self.base_url}/robots.txt"
        result = {
            "sitemaps": [],
            "disallowed": [],
            "crawl_delay": None
        }

        try:
            # Try with SSL verification first, fallback to without if needed
            response = None
            for verify_ssl in [True, False]:
                try:
                    async with httpx.AsyncClient(
                        timeout=self.settings.request_timeout,
                        follow_redirects=True,
                        verify=verify_ssl
                    ) as client:
                        response = await client.get(robots_url)
                        if response.status_code == 200:
                            break
                except Exception as e:
                    if "ssl" in str(e).lower() or "certificate" in str(e).lower():
                        if verify_ssl:
                            print(f"   ⚠️ SSL issue with robots.txt, retrying...")
                            continue
                    raise
            
            if not response or response.status_code != 200:
                return result

            content = response.text
            current_agent = None

            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.lower().startswith("user-agent:"):
                    current_agent = line.split(":", 1)[1].strip()
                elif line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url.startswith("//"):
                        sitemap_url = f"{self.scheme}:{sitemap_url}"
                    result["sitemaps"].append(sitemap_url)
                elif line.lower().startswith("disallow:") and current_agent in ("*", None):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        result["disallowed"].append(path)
                elif line.lower().startswith("crawl-delay:") and current_agent in ("*", None):
                    try:
                        result["crawl_delay"] = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass

            self.disallowed_paths = result["disallowed"]
            return result

        except Exception:
            return result

    # ============================================
    # SITEMAP PARSING
    # ============================================

    async def parse_sitemap(self, sitemap_url: str = None, depth: int = 0, max_depth: int = 3) -> list[str]:
        """
        Parse sitemap.xml and sitemap indexes recursively.
        Handles both regular sitemaps and sitemap index files (sitemaps containing links to other sitemaps).
        
        Args:
            sitemap_url: URL of the sitemap to parse
            depth: Current recursion depth (for sitemap indexes)
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns: List of discovered page URLs
        """
        if sitemap_url is None:
            sitemap_url = f"{self.base_url}/sitemap.xml"
        
        # Prevent infinite recursion
        if depth > max_depth:
            print(f"⚠️ Max sitemap depth ({max_depth}) reached, stopping recursion")
            return []

        urls = []

        try:
            # Try with SSL first, then fallback to without
            response = None
            for verify_ssl in [True, False]:
                try:
                    async with httpx.AsyncClient(
                        timeout=self.settings.request_timeout, 
                        follow_redirects=True,
                        verify=verify_ssl
                    ) as client:
                        print(f"📍 Fetching sitemap: {sitemap_url} (depth: {depth})")
                        response = await client.get(sitemap_url)
                        if response.status_code == 200:
                            break
                except Exception as e:
                    if "ssl" in str(e).lower() or "certificate" in str(e).lower():
                        if verify_ssl:
                            print(f"   ⚠️ SSL issue with sitemap, retrying...")
                            continue
                    raise
                
            if not response or response.status_code != 200:
                print(f"   ⚠️ Sitemap returned {response.status_code if response else 'no response'}")
                return urls

            content = response.content
            
            # Handle gzipped sitemaps
            if sitemap_url.endswith('.gz'):
                import gzip
                content = gzip.decompress(content)

            # Parse XML
            root = etree.fromstring(content)
            
            # Namespace for sitemap protocol
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Check if this is a sitemap INDEX (contains <sitemap> elements)
            # Sitemap indexes link to other sitemaps, not directly to pages
            # Try with namespace first
            sitemap_refs = root.xpath("//ns:sitemap/ns:loc/text()", namespaces=ns)
            
            # Fallback: try without namespace (some sitemaps don't declare it properly)
            if not sitemap_refs:
                sitemap_refs = [loc.text for loc in root.iter() 
                               if loc.tag.endswith('loc') and loc.getparent().tag.endswith('sitemap')]
            
            if sitemap_refs:
                print(f"   📁 Found sitemap INDEX with {len(sitemap_refs)} child sitemaps")
                # Recursively parse each child sitemap
                for ref in sitemap_refs:
                    if ref:
                        ref = ref.strip()
                        if ref and ref.startswith(('http://', 'https://')):
                            sub_urls = await self.parse_sitemap(ref, depth=depth + 1, max_depth=max_depth)
                            urls.extend(sub_urls)
                            print(f"      ✅ Got {len(sub_urls)} URLs from {ref}")
            else:
                # Regular sitemap - extract page URLs
                # Try with namespace first
                url_locs = root.xpath("//ns:url/ns:loc/text()", namespaces=ns)
                
                # Fallback: iterate through all loc elements under url parents
                if not url_locs:
                    url_locs = [loc.text for loc in root.iter() 
                               if loc.tag.endswith('loc') and loc.getparent().tag.endswith('url') and loc.text]
                
                urls.extend([u.strip() for u in url_locs if u.strip()])
                print(f"   📄 Found {len(urls)} page URLs in sitemap")

        except etree.XMLSyntaxError as e:
            print(f"   ⚠️ Invalid XML in sitemap: {e}")
        except Exception as e:
            print(f"   ⚠️ Error parsing sitemap: {e}")

        return urls

    # ============================================
    # HTML LINK CRAWLING
    # ============================================

    async def crawl_internal_links(self, page_url: str, html_content: str) -> list[str]:
        """
        Extract internal links from HTML content.
        """
        links = []

        try:
            soup = BeautifulSoup(html_content, "lxml")

            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]

                # Normalize the URL
                normalized = self.normalize_url(href, page_url)
                if normalized and self._is_valid_internal_url(normalized):
                    links.append(normalized)

        except Exception:
            pass

        return list(set(links))

    # ============================================
    # URL NORMALIZATION
    # ============================================

    def normalize_url(self, url: str, base_url: str = None) -> Optional[str]:
        """
        Normalize URL: remove tracking params, enforce canonical format.
        """
        if not url:
            return None

        # Skip non-HTTP URLs
        if url.startswith(("mailto:", "tel:", "javascript:", "#")):
            return None

        # Handle relative URLs
        if base_url:
            url = urljoin(base_url, url)

        try:
            parsed = urlparse(url)

            # Remove fragment
            parsed = parsed._replace(fragment="")

            # Remove common tracking parameters
            tracking_params = {
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid"
            }

            if parsed.query:
                params = parsed.query.split("&")
                filtered = [p for p in params if p.split("=")[0] not in tracking_params]
                parsed = parsed._replace(query="&".join(filtered))

            # Normalize path: remove trailing slash (except for root)
            path = parsed.path
            if path != "/" and path.endswith("/"):
                path = path.rstrip("/")
            parsed = parsed._replace(path=path)

            # Rebuild URL
            normalized = urlunparse(parsed)

            return normalized

        except Exception:
            return None

    def _is_valid_internal_url(self, url: str) -> bool:
        """Check if URL is internal and not disallowed."""
        # SSRF Check
        if not self._is_safe_url(url):
            return False

        try:
            parsed = urlparse(url)
            
            # Normalize domains for comparison (strip www.)
            url_domain = parsed.netloc.replace("www.", "")
            base_domain = self.domain.replace("www.", "")

            # Check domain
            if self.include_subdomains:
                if not url_domain.endswith(base_domain):
                    return False
            else:
                # Allow both www and non-www versions
                if url_domain != base_domain:
                    return False

            # Check against disallowed paths
            for disallowed in self.disallowed_paths:
                if disallowed.endswith("*"):
                    if parsed.path.startswith(disallowed[:-1]):
                        return False
                elif parsed.path == disallowed or parsed.path.startswith(disallowed + "/"):
                    return False

            # Skip common non-content paths
            skip_patterns = [
                r"/wp-admin", r"/wp-includes", r"/admin",
                r"\.pdf$", r"\.zip$", r"\.exe$", r"\.dmg$",
                r"/login", r"/logout", r"/signin", r"/signup",
                r"/cart", r"/checkout"
            ]
            for pattern in skip_patterns:
                if re.search(pattern, parsed.path, re.IGNORECASE):
                    return False

            return True

        except Exception:
            return False

    # ============================================
    # MAIN DISCOVERY
    # ============================================

    async def discover(self, max_pages: int = None) -> list[str]:
        """
        Main discovery method.
        Returns deduplicated list of URLs to crawl.
        """
        limit = max_pages or self.settings.max_pages

        # 1. Parse robots.txt
        robots_data = await self.parse_robots_txt()

        # 2. Parse sitemaps from robots.txt
        for sitemap_url in robots_data["sitemaps"]:
            urls = await self.parse_sitemap(sitemap_url)
            self.discovered_urls.update(urls)

        # 3. Try default sitemap if none found
        if not robots_data["sitemaps"]:
            urls = await self.parse_sitemap()
            self.discovered_urls.update(urls)

        # 4. Crawl homepage for links (with SSL fallback)
        homepage_html = None
        for verify_ssl in [True, False]:
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.request_timeout,
                    follow_redirects=True,
                    verify=verify_ssl
                ) as client:
                    response = await client.get(self.base_url)
                    if response.status_code == 200:
                        homepage_html = response.text
                        break
            except Exception as e:
                if "ssl" in str(e).lower() or "certificate" in str(e).lower():
                    if verify_ssl:
                        print(f"   ⚠️ SSL issue fetching homepage, retrying...")
                        continue
                break
        
        if homepage_html:
            links = await self.crawl_internal_links(self.base_url, homepage_html)
            self.discovered_urls.update(links)
            print(f"   📄 Found {len(links)} links on homepage")
        else:
            print(f"   ⚠️ Could not fetch homepage")

        # 5. Always include the base URL
        self.discovered_urls.add(self.base_url)

        # 6. Filter and deduplicate
        valid_urls = [
            url for url in self.discovered_urls
            if self._is_valid_internal_url(url)
        ]

        # Limit to max pages
        return list(set(valid_urls))[:limit]
