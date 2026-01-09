"""
CiteKit – Competitor Benchmarking (Comprehensive)
Full analysis of competitor AI readiness with ALL signals
"""

import asyncio
import re
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from urllib.parse import urlparse
from datetime import datetime

import httpx

from config import get_settings

# Configure logging
logger = logging.getLogger("geo-compiler.benchmark")


@dataclass
class SignalCheck:
    """Individual signal check result"""
    name: str
    key: str
    found: bool
    details: str = ""
    points: int = 0
    max_points: int = 0


@dataclass
class CompetitorResult:
    """Result of checking a competitor's AI readiness"""
    domain: str
    
    # Core AI Files
    has_llm_txt: bool = False
    llm_txt_length: int = 0
    has_mcp_json: bool = False
    has_robots_llm: bool = False
    robots_llm_bots: List[str] = field(default_factory=list)
    
    # Structured Data
    has_schema_org: bool = False
    schema_types: List[str] = field(default_factory=list)
    social_links_count: int = 0
    pricing_in_schema: bool = False
    has_faq_schema: bool = False
    has_breadcrumb_schema: bool = False
    
    # Technical SEO for AI
    has_sitemap: bool = False
    sitemap_url: str = ""
    has_security_txt: bool = False
    has_humans_txt: bool = False
    
    # Content Signals
    has_meta_description: bool = False
    meta_description_length: int = 0
    has_og_tags: bool = False
    has_twitter_cards: bool = False
    has_canonical: bool = False
    h1_count: int = 0
    
    # API/Developer Signals
    has_api_docs: bool = False
    has_openapi_spec: bool = False
    
    # Calculated
    geo_score: int = 0
    geo_status: str = "none"
    check_error: Optional[str] = None
    all_checks: List[SignalCheck] = field(default_factory=list)
    
    def calculate_score(self):
        """Calculate AI readiness score based on ALL checks"""
        self.all_checks = []
        score = 0
        
        # 1. llms.txt (25 points)
        check = SignalCheck(
            name="LLMs.txt File",
            key="llm_txt",
            found=self.has_llm_txt,
            max_points=25,
            details=f"{self.llm_txt_length} chars" if self.has_llm_txt else "Not found"
        )
        if self.has_llm_txt:
            check.points = 20
            if self.llm_txt_length > 500:
                check.points = 25
                check.details += " (comprehensive)"
        self.all_checks.append(check)
        score += check.points
        
        # 2. MCP.json (10 points)
        check = SignalCheck(
            name="MCP Configuration",
            key="mcp_json",
            found=self.has_mcp_json,
            max_points=10,
            points=10 if self.has_mcp_json else 0,
            details="Agent routing enabled" if self.has_mcp_json else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 3. Robots.txt AI Directives (10 points)
        check = SignalCheck(
            name="AI Crawler Rules",
            key="robots_llm",
            found=self.has_robots_llm,
            max_points=10,
            points=10 if self.has_robots_llm else 0,
            details=f"Bots: {', '.join(self.robots_llm_bots[:3])}" if self.robots_llm_bots else "No AI bot rules"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 4. Schema.org JSON-LD (15 points)
        check = SignalCheck(
            name="Schema.org Markup",
            key="schema_org",
            found=self.has_schema_org,
            max_points=15,
            details=f"Types: {', '.join(self.schema_types[:3])}" if self.schema_types else "Not found"
        )
        if self.has_schema_org:
            check.points = 10
            if 'Organization' in self.schema_types or 'WebSite' in self.schema_types:
                check.points = 15
        self.all_checks.append(check)
        score += check.points
        
        # 5. Social Links / sameAs (5 points)
        check = SignalCheck(
            name="Social Profile Links",
            key="social_links",
            found=self.social_links_count >= 1,
            max_points=5,
            details=f"{self.social_links_count} links found"
        )
        if self.social_links_count >= 3:
            check.points = 5
        elif self.social_links_count >= 1:
            check.points = 3
        self.all_checks.append(check)
        score += check.points
        
        # 6. FAQ Schema (5 points)
        check = SignalCheck(
            name="FAQ Schema",
            key="faq_schema",
            found=self.has_faq_schema,
            max_points=5,
            points=5 if self.has_faq_schema else 0,
            details="FAQ structured data" if self.has_faq_schema else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 7. Breadcrumb Schema (3 points)
        check = SignalCheck(
            name="Breadcrumb Schema",
            key="breadcrumb_schema",
            found=self.has_breadcrumb_schema,
            max_points=3,
            points=3 if self.has_breadcrumb_schema else 0,
            details="Navigation structured data" if self.has_breadcrumb_schema else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 8. Pricing Schema (5 points)
        check = SignalCheck(
            name="Pricing Schema",
            key="pricing_schema",
            found=self.pricing_in_schema,
            max_points=5,
            points=5 if self.pricing_in_schema else 0,
            details="Offer/Price data found" if self.pricing_in_schema else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 9. XML Sitemap (5 points)
        check = SignalCheck(
            name="XML Sitemap",
            key="sitemap",
            found=self.has_sitemap,
            max_points=5,
            points=5 if self.has_sitemap else 0,
            details=self.sitemap_url if self.has_sitemap else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 10. Meta Description (3 points)
        check = SignalCheck(
            name="Meta Description",
            key="meta_description",
            found=self.has_meta_description,
            max_points=3,
            details=f"{self.meta_description_length} chars" if self.has_meta_description else "Missing"
        )
        if self.has_meta_description:
            check.points = 2 if self.meta_description_length < 120 else 3
        self.all_checks.append(check)
        score += check.points
        
        # 11. Open Graph Tags (3 points)
        check = SignalCheck(
            name="Open Graph Tags",
            key="og_tags",
            found=self.has_og_tags,
            max_points=3,
            points=3 if self.has_og_tags else 0,
            details="Social sharing optimized" if self.has_og_tags else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 12. Twitter Cards (2 points)
        check = SignalCheck(
            name="Twitter Cards",
            key="twitter_cards",
            found=self.has_twitter_cards,
            max_points=2,
            points=2 if self.has_twitter_cards else 0,
            details="Twitter preview enabled" if self.has_twitter_cards else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 13. Canonical URL (2 points)
        check = SignalCheck(
            name="Canonical URL",
            key="canonical",
            found=self.has_canonical,
            max_points=2,
            points=2 if self.has_canonical else 0,
            details="Duplicate content prevention" if self.has_canonical else "Not set"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 14. H1 Tags (2 points)
        check = SignalCheck(
            name="H1 Heading",
            key="h1_count",
            found=self.h1_count == 1,
            max_points=2,
            details=f"{self.h1_count} H1 tag(s)"
        )
        if self.h1_count == 1:
            check.points = 2
        elif self.h1_count > 0:
            check.points = 1
        self.all_checks.append(check)
        score += check.points
        
        # 15. Security.txt (2 points)
        check = SignalCheck(
            name="Security.txt",
            key="security_txt",
            found=self.has_security_txt,
            max_points=2,
            points=2 if self.has_security_txt else 0,
            details="Security contact info" if self.has_security_txt else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        # 16. OpenAPI Spec (3 points) - for SaaS/API companies
        check = SignalCheck(
            name="OpenAPI/Swagger",
            key="openapi",
            found=self.has_openapi_spec,
            max_points=3,
            points=3 if self.has_openapi_spec else 0,
            details="API documentation" if self.has_openapi_spec else "Not found"
        )
        self.all_checks.append(check)
        score += check.points
        
        self.geo_score = min(score, 100)
        
        # Determine status
        if self.geo_score >= 70:
            self.geo_status = "advanced"
        elif self.geo_score >= 40:
            self.geo_status = "moderate"
        elif self.geo_score >= 20:
            self.geo_status = "basic"
        else:
            self.geo_status = "none"
        
        return self.geo_score


class CompetitorBenchmark:
    """
    Comprehensive competitor AI readiness checker.
    Analyzes homepage for ALL key signals.
    """

    def __init__(self):
        self.settings = get_settings()
        self.timeout = 12

    async def check_competitor(self, url: str) -> CompetitorResult:
        """
        Full check a competitor for ALL AI readiness signals.
        """
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        result = CompetitorResult(domain=domain)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; CiteKit/1.0; +https://wantaiseo.com)'
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            # Run all checks concurrently
            await asyncio.gather(
                self._check_llm_files(client, base_url, result),
                self._check_robots(client, base_url, result),
                self._check_sitemap(client, base_url, result),
                self._check_homepage(client, base_url, result),
                self._check_well_known(client, base_url, result),
                self._check_api_docs(client, base_url, result),
                return_exceptions=True
            )

        # Calculate final score
        result.calculate_score()
        
        return result
    
    async def _check_llm_files(self, client: httpx.AsyncClient, base_url: str, result: CompetitorResult):
        """Check for llms.txt and mcp.json"""
        # llms.txt
        try:
            for path in ['/llms.txt', '/llm.txt', '/.well-known/llms.txt']:
                resp = await client.get(f"{base_url}{path}")
                if resp.status_code == 200 and len(resp.text) > 50:
                    if '#' in resp.text or 'http' in resp.text.lower():
                        result.has_llm_txt = True
                        result.llm_txt_length = len(resp.text)
                        break
        except:
            pass
        
        # mcp.json
        try:
            for path in ['/mcp.json', '/.well-known/mcp.json']:
                resp = await client.get(f"{base_url}{path}")
                if resp.status_code == 200:
                    if '"endpoints"' in resp.text or '"site"' in resp.text:
                        result.has_mcp_json = True
                        break
        except:
            pass
    
    async def _check_robots(self, client: httpx.AsyncClient, base_url: str, result: CompetitorResult):
        """Check robots.txt for AI bot directives"""
        try:
            resp = await client.get(f"{base_url}/robots.txt")
            if resp.status_code == 200:
                text = resp.text.lower()
                llm_bots = {
                    'gptbot': 'GPTBot',
                    'chatgpt': 'ChatGPT-User',
                    'anthropic': 'Anthropic',
                    'claude': 'ClaudeBot',
                    'perplexity': 'PerplexityBot',
                    'cohere': 'Cohere-AI',
                    'google-extended': 'Google-Extended',
                    'ccbot': 'CCBot',
                    'bytespider': 'Bytespider'
                }
                
                found_bots = []
                for key, name in llm_bots.items():
                    if key in text:
                        found_bots.append(name)
                
                if found_bots:
                    result.has_robots_llm = True
                    result.robots_llm_bots = found_bots
        except:
            pass
    
    async def _check_sitemap(self, client: httpx.AsyncClient, base_url: str, result: CompetitorResult):
        """Check for XML sitemap"""
        try:
            for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap-index.xml']:
                resp = await client.get(f"{base_url}{path}")
                if resp.status_code == 200 and ('<?xml' in resp.text or '<urlset' in resp.text or '<sitemapindex' in resp.text):
                    result.has_sitemap = True
                    result.sitemap_url = f"{base_url}{path}"
                    break
        except:
            pass
    
    async def _check_homepage(self, client: httpx.AsyncClient, base_url: str, result: CompetitorResult):
        """Check homepage for various signals"""
        try:
            resp = await client.get(base_url)
            if resp.status_code == 200:
                html = resp.text
                
                # Schema.org JSON-LD
                self._extract_schema_info(html, result)
                
                # Meta description
                meta_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
                if not meta_match:
                    meta_match = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']', html, re.I)
                if meta_match:
                    result.has_meta_description = True
                    result.meta_description_length = len(meta_match.group(1))
                
                # Open Graph
                if 'og:title' in html or 'og:description' in html:
                    result.has_og_tags = True
                
                # Twitter Cards
                if 'twitter:card' in html or 'twitter:title' in html:
                    result.has_twitter_cards = True
                
                # Canonical
                if 'rel="canonical"' in html or "rel='canonical'" in html:
                    result.has_canonical = True
                
                # H1 count
                h1_matches = re.findall(r'<h1[^>]*>', html, re.I)
                result.h1_count = len(h1_matches)
                
        except:
            pass
    
    async def _check_well_known(self, client: httpx.AsyncClient, base_url: str, result: CompetitorResult):
        """Check .well-known files"""
        try:
            resp = await client.get(f"{base_url}/.well-known/security.txt")
            if resp.status_code == 200 and ('Contact:' in resp.text or 'contact:' in resp.text.lower()):
                result.has_security_txt = True
        except:
            pass
        
        try:
            resp = await client.get(f"{base_url}/humans.txt")
            if resp.status_code == 200 and len(resp.text) > 20:
                result.has_humans_txt = True
        except:
            pass
    
    async def _check_api_docs(self, client: httpx.AsyncClient, base_url: str, result: CompetitorResult):
        """Check for API documentation"""
        try:
            for path in ['/docs', '/api-docs', '/swagger', '/api/docs', '/openapi.json', '/swagger.json']:
                resp = await client.get(f"{base_url}{path}")
                if resp.status_code == 200:
                    if 'openapi' in resp.text.lower() or 'swagger' in resp.text.lower():
                        result.has_openapi_spec = True
                        result.has_api_docs = True
                        break
                    elif 'api' in path and '<html' in resp.text.lower():
                        result.has_api_docs = True
        except:
            pass
    
    def _extract_schema_info(self, html: str, result: CompetitorResult) -> CompetitorResult:
        """Extract Schema.org information from HTML"""
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(jsonld_pattern, html, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                result.has_schema_org = True
                
                items = data.get('@graph', [data]) if isinstance(data, dict) else [data]
                
                for item in items:
                    if isinstance(item, dict):
                        schema_type = item.get('@type', '')
                        if isinstance(schema_type, list):
                            result.schema_types.extend(schema_type)
                        elif schema_type:
                            result.schema_types.append(schema_type)
                        
                        # sameAs links
                        same_as = item.get('sameAs', [])
                        if isinstance(same_as, str):
                            result.social_links_count += 1
                        elif isinstance(same_as, list):
                            result.social_links_count += len(same_as)
                        
                        # Offers/pricing
                        if item.get('offers') or item.get('makesOffer') or item.get('priceRange'):
                            result.pricing_in_schema = True
                        
                        # FAQ Schema
                        if schema_type == 'FAQPage' or 'FAQPage' in str(schema_type):
                            result.has_faq_schema = True
                        
                        # Breadcrumb
                        if 'BreadcrumbList' in str(schema_type):
                            result.has_breadcrumb_schema = True
                            
            except json.JSONDecodeError:
                pass
        
        result.schema_types = list(set(result.schema_types))
        return result

    async def benchmark_competitors(self, competitors: List[str]) -> List[CompetitorResult]:
        """Check multiple competitors concurrently."""
        tasks = [self.check_competitor(url) for url in competitors[:5]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = CompetitorResult(domain=competitors[i], check_error=str(result))
                error_result.calculate_score()
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results

    def generate_comparison_report(
        self,
        your_domain: str,
        your_score: int,
        your_result: CompetitorResult,
        competitors: List[CompetitorResult]
    ) -> Dict:
        """
        Generate structured comparison data for frontend rendering.
        Rankings based on CURRENT score only.
        """
        # Build comparison table with all sites
        all_sites = [your_result] + competitors
        
        # Sort by CURRENT score (not potential) - You are not treated specially
        all_sites_sorted = sorted(all_sites, key=lambda x: -x.geo_score)
        
        # Find your rank based on CURRENT score
        your_rank = next(
            (i + 1 for i, site in enumerate(all_sites_sorted) if site.domain == your_domain),
            len(all_sites_sorted)
        )
        
        comparison_table = []
        for rank, site in enumerate(all_sites_sorted, 1):
            comparison_table.append({
                "rank": rank,
                "domain": site.domain,
                "is_you": site.domain == your_domain,
                "score": site.geo_score,
                "status": site.geo_status,
                "checks": [
                    {
                        "name": check.name,
                        "key": check.key,
                        "found": check.found,
                        "points": check.points,
                        "max_points": check.max_points,
                        "details": check.details
                    }
                    for check in site.all_checks
                ]
            })
        
        # Generate gaps to close
        gaps = self._identify_gaps(your_result, competitors)
        
        # Key insights
        insights = self._generate_insights(your_result, competitors, your_rank, len(all_sites))
        
        # Summary stats
        avg_score = sum(c.geo_score for c in competitors) / len(competitors) if competitors else 0
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "your_domain": your_domain,
            "your_current_score": your_score,
            "your_rank": your_rank,
            "total_compared": len(all_sites),
            "average_competitor_score": round(avg_score, 1),
            "comparison_table": comparison_table,
            "gaps_to_close": gaps,
            "insights": insights,
            "summary": self._generate_summary(your_result, competitors, your_rank)
        }
    
    def _identify_gaps(self, your_result: CompetitorResult, competitors: List[CompetitorResult]) -> List[Dict]:
        """Identify what competitors have that you don't"""
        gaps = []
        
        gap_definitions = [
            ("has_llm_txt", "llms.txt", "high", "Deploy llms.txt to your site root", "AI models can better understand your site"),
            ("has_mcp_json", "MCP Configuration", "medium", "Add mcp.json for AI agent routing", "AI agents can navigate directly to pages"),
            ("has_robots_llm", "AI Crawler Rules", "high", "Add GPTBot/ClaudeBot rules to robots.txt", "Control AI crawler access"),
            ("has_schema_org", "Schema.org Markup", "high", "Add Organization JSON-LD", "Better entity recognition by AI"),
            ("has_faq_schema", "FAQ Schema", "medium", "Add FAQPage structured data", "AI can cite your FAQ answers"),
            ("has_sitemap", "XML Sitemap", "medium", "Add sitemap.xml", "Helps AI crawlers discover pages"),
            ("has_meta_description", "Meta Description", "low", "Add meta description tags", "Improves AI summaries"),
            ("has_og_tags", "Open Graph Tags", "low", "Add og:title and og:description", "Better social and AI previews"),
        ]
        
        for attr, feature, priority, action, impact in gap_definitions:
            your_value = getattr(your_result, attr, False)
            competitors_with = [c for c in competitors if getattr(c, attr, False)]
            
            if not your_value and competitors_with:
                gaps.append({
                    "feature": feature,
                    "priority": priority,
                    "you_have": False,
                    "competitors_have": len(competitors_with),
                    "action": action,
                    "impact": impact
                })
        
        # Special case for social links
        if your_result.social_links_count < 2:
            competitors_with_social = [c for c in competitors if c.social_links_count >= 2]
            if competitors_with_social:
                gaps.append({
                    "feature": "Social Profile Links",
                    "priority": "medium",
                    "you_have": False,
                    "competitors_have": len(competitors_with_social),
                    "action": "Add sameAs links to your Schema.org markup",
                    "impact": "Stronger entity disambiguation"
                })
        
        return sorted(gaps, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])
    
    def _generate_insights(self, your_result: CompetitorResult, competitors: List[CompetitorResult], rank: int, total: int) -> List[str]:
        """Generate key insights from the comparison"""
        insights = []
        
        # Rank insight
        if rank == 1:
            insights.append(f"🏆 You're #1 out of {total} sites! You lead in AI readiness.")
        elif rank == 2:
            leader = max(competitors, key=lambda c: c.geo_score)
            gap = leader.geo_score - your_result.geo_score
            insights.append(f"You're #{rank} out of {total}. {leader.domain} leads by {gap} points.")
        else:
            insights.append(f"You're ranked #{rank} out of {total}. There's room to improve!")
        
        # Competition level
        avg_score = sum(c.geo_score for c in competitors) / len(competitors) if competitors else 0
        if avg_score < 25:
            insights.append("🚀 Low competition! Most competitors haven't optimized for AI yet.")
        elif avg_score > 50:
            insights.append("⚡ High competition! Your competitors are investing in AI visibility.")
        
        # What you're missing that others have
        missing_critical = []
        if not your_result.has_llm_txt and any(c.has_llm_txt for c in competitors):
            missing_critical.append("llms.txt")
        if not your_result.has_schema_org and any(c.has_schema_org for c in competitors):
            missing_critical.append("Schema.org")
        
        if missing_critical:
            insights.append(f"❌ You're missing: {', '.join(missing_critical)} (competitors have it)")
        
        # What you have that others don't
        advantages = []
        if your_result.has_llm_txt and not any(c.has_llm_txt for c in competitors):
            advantages.append("llms.txt")
        if your_result.has_schema_org and not any(c.has_schema_org for c in competitors):
            advantages.append("Schema.org")
        
        if advantages:
            insights.append(f"✅ Your advantage: You have {', '.join(advantages)} (competitors don't)")
        
        return insights[:5]
    
    def _generate_summary(self, your_result: CompetitorResult, competitors: List[CompetitorResult], rank: int) -> str:
        """Generate a brief summary"""
        total = len(competitors) + 1
        avg_score = sum(c.geo_score for c in competitors) / len(competitors) if competitors else 0
        
        if rank == 1:
            return f"Excellent! You lead the {total}-site competitive set with a score of {your_result.geo_score}/100."
        elif your_result.geo_score >= avg_score:
            return f"Good progress! Your score ({your_result.geo_score}/100) is above the average ({avg_score:.0f}/100)."
        else:
            return f"Opportunity ahead! Your score ({your_result.geo_score}/100) is below average ({avg_score:.0f}/100). Deploy the fixes to catch up!"

    def generate_markdown_report(
        self,
        your_domain: str,
        your_score: int,
        your_result: CompetitorResult,
        competitors: List[CompetitorResult]
    ) -> str:
        """
        Generate markdown benchmark report for ZIP package.
        """
        total = len(competitors)
        avg_score = sum(c.geo_score for c in competitors) / total if total > 0 else 0
        
        # Rank based on current score
        all_scores = [(your_domain, your_score)] + [(c.domain, c.geo_score) for c in competitors]
        all_scores_sorted = sorted(all_scores, key=lambda x: -x[1])
        your_rank = next(i + 1 for i, (domain, _) in enumerate(all_scores_sorted) if domain == your_domain)

        report = f"""## 🏆 Competitor Benchmark Report

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  
**Your Domain:** {your_domain}  
**Your Rank:** #{your_rank} of {total + 1}

---

### Your Position (Current State)

| Metric | Your Score | Avg Competitor |
|--------|-----------|----------------|
| **AI Readiness** | {your_score}/100 | {avg_score:.0f}/100 |

---

### Full Comparison (Ranked by Current Score)

| Rank | Domain | Score | llms.txt | Schema | AI Bots | Sitemap | Status |
|------|--------|-------|----------|--------|---------|---------|--------|
"""
        # Add your site
        llm = "✅" if your_result.has_llm_txt else "❌"
        schema = "✅" if your_result.has_schema_org else "❌"
        robots = "✅" if your_result.has_robots_llm else "❌"
        sitemap = "✅" if your_result.has_sitemap else "❌"
        
        all_sites = [(your_domain, your_score, your_result, True)]
        for c in competitors:
            all_sites.append((c.domain, c.geo_score, c, False))
        
        all_sites_sorted = sorted(all_sites, key=lambda x: -x[1])
        
        for rank, (domain, score, site, is_you) in enumerate(all_sites_sorted, 1):
            llm = "✅" if site.has_llm_txt else "❌"
            schema = "✅" if site.has_schema_org else "❌"
            robots = "✅" if site.has_robots_llm else "❌"
            sitemap = "✅" if site.has_sitemap else "❌"
            
            status_emoji = {
                "advanced": "🟢 Advanced",
                "moderate": "🟡 Moderate",
                "basic": "🟠 Basic",
                "none": "🔴 None"
            }
            status = status_emoji.get(site.geo_status, "❓")
            marker = " **← YOU**" if is_you else ""
            
            report += f"| #{rank} | {domain}{marker} | {score}/100 | {llm} | {schema} | {robots} | {sitemap} | {status} |\n"

        report += f"""

---

### All Signal Checks Legend

| Signal | What It Means | Points |
|--------|---------------|--------|
| **llms.txt** | Machine-readable site description for LLMs | 25 |
| **MCP.json** | AI agent routing configuration | 10 |
| **AI Bot Rules** | GPTBot/ClaudeBot directives in robots.txt | 10 |
| **Schema.org** | JSON-LD structured data | 15 |
| **FAQ Schema** | FAQPage structured data | 5 |
| **Social Links** | sameAs links for entity disambiguation | 5 |
| **Sitemap** | XML sitemap for crawlers | 5 |
| **Meta Description** | Page summary for AI | 3 |
| **Open Graph** | Social sharing metadata | 3 |
| **Canonical URL** | Duplicate content prevention | 2 |

---

### Key Takeaways

"""
        if your_rank == 1:
            report += f"🏆 **Congratulations!** You're leading the pack with the highest AI readiness score.\n\n"
        elif avg_score < 30:
            report += f"🚀 **Low competition!** Average competitor score is only {avg_score:.0f}/100. You have a first-mover advantage.\n\n"
        else:
            report += f"⚡ **Room to grow!** Deploy your CiteKit files to climb from #{your_rank} to #1.\n\n"

        report += "*Deploy your generated files to improve your competitive position!*\n"

        return report


async def run_benchmark(your_domain: str, your_score: int, competitor_urls: List[str]) -> str:
    """Run competitor benchmark and return markdown report."""
    if not competitor_urls:
        return ""
    
    benchmark = CompetitorBenchmark()
    competitors = await benchmark.benchmark_competitors(competitor_urls)
    
    # Create your result for comparison
    your_result = CompetitorResult(domain=your_domain)
    your_result.geo_score = your_score
    your_result.calculate_score()
    
    return benchmark.generate_markdown_report(your_domain, your_score, your_result, competitors)


async def run_full_benchmark(
    your_domain: str, 
    your_score: int, 
    your_html: str,
    competitor_urls: List[str]
) -> Dict:
    """
    Run full benchmark with structured comparison data.
    Rankings based on CURRENT score only.
    """
    benchmark = CompetitorBenchmark()
    
    # Create your result based on CURRENT state (what's actually deployed)
    # We could also run a check on your own site for accuracy
    your_result = CompetitorResult(domain=your_domain)
    
    # If HTML provided, extract what you CURRENTLY have deployed
    if your_html:
        benchmark._extract_schema_info(your_html, your_result)
    
    # Set your current score
    your_result.geo_score = your_score
    your_result.calculate_score()
    
    # Run competitor checks
    competitors = await benchmark.benchmark_competitors(competitor_urls)
    
    return benchmark.generate_comparison_report(
        your_domain, 
        your_score, 
        your_result, 
        competitors
    )
