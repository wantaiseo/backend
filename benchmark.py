"""
CiteKit – Competitor Benchmarking (Enhanced)
Quick lightweight analysis of competitor AI readiness
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
class CompetitorResult:
    """Result of checking a competitor's AI readiness"""
    domain: str
    has_llm_txt: bool = False
    has_mcp_json: bool = False
    has_robots_llm: bool = False  # LLM directives in robots.txt
    has_schema_org: bool = False  # Schema.org JSON-LD present
    schema_types: List[str] = field(default_factory=list)  # Organization, Product, etc.
    social_links_count: int = 0  # sameAs links found
    llm_txt_length: int = 0
    pricing_in_schema: bool = False  # Has Offer/PriceSpecification
    geo_score: int = 0  # Calculated score 0-100
    geo_status: str = "none"  # none, basic, moderate, advanced
    check_error: Optional[str] = None
    
    def calculate_score(self):
        """Calculate AI readiness score based on checks"""
        score = 0
        
        # llm.txt presence (25 points)
        if self.has_llm_txt:
            score += 25
            # Bonus for content length
            if self.llm_txt_length > 500:
                score += 5
        
        # mcp.json presence (15 points)
        if self.has_mcp_json:
            score += 15
        
        # robots.txt LLM directives (10 points)
        if self.has_robots_llm:
            score += 10
        
        # Schema.org presence (20 points)
        if self.has_schema_org:
            score += 20
            # Bonus for Organization type
            if 'Organization' in self.schema_types:
                score += 5
        
        # Social links (10 points)
        if self.social_links_count >= 2:
            score += 10
        elif self.social_links_count >= 1:
            score += 5
        
        # Pricing in schema (10 points)
        if self.pricing_in_schema:
            score += 10
        
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
    Fast competitor AI readiness checker.
    Analyzes homepage + pricing page for key signals.
    """

    def __init__(self):
        self.settings = get_settings()
        self.timeout = 10  # Fast timeout

    async def check_competitor(self, url: str) -> CompetitorResult:
        """
        Quick check a competitor for AI readiness signals.
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
            # 1. Check llm.txt / llms.txt
            try:
                for path in ['/llms.txt', '/llm.txt', '/.well-known/llms.txt']:
                    resp = await client.get(f"{base_url}{path}")
                    if resp.status_code == 200 and len(resp.text) > 50:
                        # Verify it's actually an llm.txt (has # headers typically)
                        if '#' in resp.text or 'http' in resp.text.lower():
                            result.has_llm_txt = True
                            result.llm_txt_length = len(resp.text)
                            break
            except Exception:
                pass

            # 2. Check mcp.json
            try:
                for path in ['/mcp.json', '/.well-known/mcp.json']:
                    resp = await client.get(f"{base_url}{path}")
                    if resp.status_code == 200:
                        text = resp.text
                        if '"endpoints"' in text or '"site"' in text:
                            result.has_mcp_json = True
                            break
            except Exception:
                pass

            # 3. Check robots.txt for LLM directives
            try:
                resp = await client.get(f"{base_url}/robots.txt")
                if resp.status_code == 200:
                    text = resp.text.lower()
                    llm_keywords = ['gptbot', 'chatgpt', 'anthropic', 'claude', 'llm', 
                                   'perplexity', 'cohere', 'google-extended']
                    if any(kw in text for kw in llm_keywords):
                        result.has_robots_llm = True
            except Exception:
                pass

            # 4. Check homepage for Schema.org JSON-LD
            try:
                resp = await client.get(base_url)
                if resp.status_code == 200:
                    html = resp.text
                    result = self._extract_schema_info(html, result)
            except Exception:
                pass

            # 5. Quick check pricing page for offers
            try:
                for path in ['/pricing', '/plans', '/price']:
                    resp = await client.get(f"{base_url}{path}")
                    if resp.status_code == 200:
                        html = resp.text
                        # Check for pricing schema
                        if 'PriceSpecification' in html or '"Offer"' in html or '"price"' in html.lower():
                            result.pricing_in_schema = True
                        break
            except Exception:
                pass

        # Calculate final score
        result.calculate_score()
        
        return result
    
    def _extract_schema_info(self, html: str, result: CompetitorResult) -> CompetitorResult:
        """Extract Schema.org information from HTML"""
        # Find JSON-LD scripts
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(jsonld_pattern, html, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                result.has_schema_org = True
                
                # Handle @graph structure
                items = data.get('@graph', [data]) if isinstance(data, dict) else [data]
                
                for item in items:
                    if isinstance(item, dict):
                        schema_type = item.get('@type', '')
                        if isinstance(schema_type, list):
                            result.schema_types.extend(schema_type)
                        elif schema_type:
                            result.schema_types.append(schema_type)
                        
                        # Check for sameAs links
                        same_as = item.get('sameAs', [])
                        if isinstance(same_as, str):
                            result.social_links_count += 1
                        elif isinstance(same_as, list):
                            result.social_links_count += len(same_as)
                        
                        # Check for offers/pricing
                        if item.get('offers') or item.get('makesOffer') or item.get('priceRange'):
                            result.pricing_in_schema = True
                            
            except json.JSONDecodeError:
                pass
        
        # Deduplicate schema types
        result.schema_types = list(set(result.schema_types))
        
        return result

    async def benchmark_competitors(self, competitors: List[str]) -> List[CompetitorResult]:
        """
        Check multiple competitors concurrently.
        """
        tasks = [self.check_competitor(url) for url in competitors[:5]]  # Max 5 competitors
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CompetitorResult(
                    domain=competitors[i],
                    check_error=str(result)
                ))
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
        """
        # Build comparison table data
        all_sites = [your_result] + competitors
        
        comparison_table = []
        for site in all_sites:
            comparison_table.append({
                "domain": site.domain,
                "is_you": site.domain == your_domain,
                "score": site.geo_score,
                "status": site.geo_status,
                "has_llm_txt": site.has_llm_txt,
                "has_mcp_json": site.has_mcp_json,
                "has_robots_llm": site.has_robots_llm,
                "has_schema_org": site.has_schema_org,
                "schema_types": site.schema_types[:3],  # Top 3 types
                "social_links": site.social_links_count,
                "has_pricing": site.pricing_in_schema,
            })
        
        # Sort by score (your site always first)
        comparison_table.sort(key=lambda x: (-x["is_you"], -x["score"]))
        
        # Generate gaps to close
        gaps = self._identify_gaps(your_result, competitors)
        
        # Calculate your rank
        scores = [your_score] + [c.geo_score for c in competitors]
        your_rank = sorted(scores, reverse=True).index(your_score) + 1
        
        # Key insights
        insights = self._generate_insights(your_result, competitors, your_rank)
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "your_domain": your_domain,
            "your_score": your_score,
            "your_rank": your_rank,
            "total_compared": len(all_sites),
            "comparison_table": comparison_table,
            "gaps_to_close": gaps,
            "insights": insights,
            "summary": self._generate_summary(your_result, competitors, your_rank)
        }
    
    def _identify_gaps(self, your_result: CompetitorResult, competitors: List[CompetitorResult]) -> List[Dict]:
        """Identify what competitors have that you don't"""
        gaps = []
        
        # Check each feature competitors have
        competitors_with_llm = [c for c in competitors if c.has_llm_txt]
        competitors_with_mcp = [c for c in competitors if c.has_mcp_json]
        competitors_with_robots = [c for c in competitors if c.has_robots_llm]
        competitors_with_schema = [c for c in competitors if c.has_schema_org]
        competitors_with_social = [c for c in competitors if c.social_links_count >= 2]
        competitors_with_pricing = [c for c in competitors if c.pricing_in_schema]
        
        if not your_result.has_llm_txt and competitors_with_llm:
            gaps.append({
                "feature": "llms.txt",
                "priority": "high",
                "competitors_have": len(competitors_with_llm),
                "action": "Deploy llms.txt to your site root",
                "impact": "AI models can better understand your site structure"
            })
        
        if not your_result.has_mcp_json and competitors_with_mcp:
            gaps.append({
                "feature": "mcp.json",
                "priority": "medium",
                "competitors_have": len(competitors_with_mcp),
                "action": "Add mcp.json for AI agent routing",
                "impact": "AI agents can navigate directly to relevant pages"
            })
        
        if not your_result.has_robots_llm and competitors_with_robots:
            gaps.append({
                "feature": "AI Crawler Directives",
                "priority": "high",
                "competitors_have": len(competitors_with_robots),
                "action": "Add GPTBot/ClaudeBot rules to robots.txt",
                "impact": "Control how AI crawlers access your content"
            })
        
        if not your_result.has_schema_org and competitors_with_schema:
            gaps.append({
                "feature": "Schema.org Markup",
                "priority": "high",
                "competitors_have": len(competitors_with_schema),
                "action": "Add Organization JSON-LD to your homepage",
                "impact": "Better entity recognition by AI systems"
            })
        
        if your_result.social_links_count < 2 and competitors_with_social:
            gaps.append({
                "feature": "Social Profile Links",
                "priority": "medium",
                "competitors_have": len(competitors_with_social),
                "action": "Add sameAs links to your Schema.org markup",
                "impact": "Stronger entity disambiguation for AI"
            })
        
        if not your_result.pricing_in_schema and competitors_with_pricing:
            gaps.append({
                "feature": "Pricing Schema",
                "priority": "low",
                "competitors_have": len(competitors_with_pricing),
                "action": "Add Offer schema to pricing pages",
                "impact": "AI can cite accurate pricing information"
            })
        
        return gaps
    
    def _generate_insights(self, your_result: CompetitorResult, competitors: List[CompetitorResult], rank: int) -> List[str]:
        """Generate key insights from the comparison"""
        insights = []
        total = len(competitors) + 1
        
        if rank == 1:
            insights.append(f"🏆 You're leading your competitive set with the highest AI readiness score!")
        elif rank <= 2:
            leader = max(competitors, key=lambda c: c.geo_score)
            insights.append(f"You're #{rank} out of {total}. {leader.domain} leads with {leader.geo_score}/100.")
        else:
            insights.append(f"You're ranked #{rank} out of {total} in AI readiness.")
        
        # Check for first-mover advantage
        competitors_with_geo = sum(1 for c in competitors if c.geo_score >= 40)
        if competitors_with_geo == 0:
            insights.append("🚀 None of your competitors have significant AI optimization yet - first mover advantage!")
        
        # Check specific advantages you have
        if your_result.has_llm_txt and not any(c.has_llm_txt for c in competitors):
            insights.append("✅ You're the only one with an llms.txt file - major competitive advantage!")
        
        if your_result.has_schema_org and not any(c.has_schema_org for c in competitors):
            insights.append("✅ You're the only one with Schema.org markup - better AI entity recognition!")
        
        return insights[:4]  # Max 4 insights
    
    def _generate_summary(self, your_result: CompetitorResult, competitors: List[CompetitorResult], rank: int) -> str:
        """Generate a brief summary"""
        total = len(competitors) + 1
        avg_score = (your_result.geo_score + sum(c.geo_score for c in competitors)) / total
        
        if rank == 1:
            return f"Excellent! You lead your {total}-site competitive set with a score of {your_result.geo_score}/100."
        elif your_result.geo_score >= avg_score:
            return f"Good progress! Your score of {your_result.geo_score}/100 is above the average of {avg_score:.0f}/100."
        else:
            return f"Opportunity ahead! Your score of {your_result.geo_score}/100 is below the average of {avg_score:.0f}/100. Deploy the recommended fixes to catch up."

    def generate_markdown_report(
        self,
        your_domain: str,
        your_score: int,
        competitors: List[CompetitorResult]
    ) -> str:
        """
        Generate markdown benchmark report for ZIP package.
        """
        total = len(competitors)
        with_llm = sum(1 for c in competitors if c.has_llm_txt)
        with_schema = sum(1 for c in competitors if c.has_schema_org)
        avg_score = sum(c.geo_score for c in competitors) / total if total > 0 else 0

        report = f"""## 🏆 Competitor Benchmark Report

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**Your Domain:** {your_domain}

---

### Your Position

| Metric | You | Competition Average |
|--------|-----|---------------------|
| **AI Readiness Score** | {your_score}/100 | {avg_score:.0f}/100 |
| **Has llms.txt** | ✅ After Deploy | {with_llm}/{total} |
| **Has Schema.org** | ✅ After Deploy | {with_schema}/{total} |

---

### Competitor Comparison

| Domain | Score | llms.txt | Schema | Social Links | Status |
|--------|-------|----------|--------|--------------|--------|
"""

        for c in sorted(competitors, key=lambda x: -x.geo_score):
            llm = "✅" if c.has_llm_txt else "❌"
            schema = "✅" if c.has_schema_org else "❌"
            social = f"{c.social_links_count}" if c.social_links_count else "0"
            
            status_emoji = {
                "advanced": "🟢 Advanced",
                "moderate": "🟡 Moderate",
                "basic": "🟠 Basic",
                "none": "🔴 None"
            }
            status = status_emoji.get(c.geo_status, "❓")
            
            report += f"| {c.domain} | {c.geo_score}/100 | {llm} | {schema} | {social} | {status} |\n"

        if avg_score < 30:
            report += f"""
---

### 🎯 Key Insight

**Low competition in AI optimization!**

Average competitor score is only {avg_score:.0f}/100. By deploying your GEO package, 
you'll have a significant first-mover advantage in AI discoverability.

"""

        report += """
---

### What These Metrics Mean

- **Score**: Overall AI readiness (0-100)
- **llms.txt**: Machine-readable site description for LLMs
- **Schema**: JSON-LD structured data on homepage
- **Social Links**: sameAs links for entity disambiguation
- **Status**: Advanced (70+), Moderate (40-69), Basic (20-39), None (<20)

*Deploy your generated files to improve your competitive position!*
"""

        return report


async def run_benchmark(your_domain: str, your_score: int, competitor_urls: List[str]) -> str:
    """
    Run competitor benchmark and return markdown report.
    """
    if not competitor_urls:
        return ""
    
    benchmark = CompetitorBenchmark()
    results = await benchmark.benchmark_competitors(competitor_urls)
    return benchmark.generate_markdown_report(your_domain, your_score, results)


async def run_full_benchmark(
    your_domain: str, 
    your_score: int, 
    your_html: str,
    competitor_urls: List[str]
) -> Dict:
    """
    Run full benchmark with structured comparison data.
    Returns JSON-serializable dict for frontend.
    """
    benchmark = CompetitorBenchmark()
    
    # Create your result from available data
    # NOTE: These files are GENERATED but not yet DEPLOYED, so mark as False
    # This gives an accurate comparison showing what competitors have live vs what you're about to deploy
    your_result = CompetitorResult(domain=your_domain)
    your_result.has_llm_txt = False  # Generated but not deployed yet
    your_result.has_mcp_json = False  # Generated but not deployed yet
    your_result.has_schema_org = False  # Generated but not deployed yet
    your_result.geo_score = your_score
    
    # Extract schema info from your homepage if provided
    if your_html:
        your_result = benchmark._extract_schema_info(your_html, your_result)
    
    # Run competitor checks
    competitors = await benchmark.benchmark_competitors(competitor_urls)
    
    return benchmark.generate_comparison_report(
        your_domain, 
        your_score, 
        your_result, 
        competitors
    )
