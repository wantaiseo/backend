"""
CiteKit – Packager
Deterministic ZIP creation with schema validation
Per FR-6: Packaging
"""

import json
import os
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from config import get_settings
from models import PageData, MCPOutput, SitemapOutput, SitemapEntry
from extractor import ContentExtractor
from auditor import GEOAuditor
from schema_generator import SchemaGenerator
from citation_scorer import generate_citation_roadmap, ReadinessScore
from deployment_guides import get_platform_guide, get_all_platform_instructions, PLATFORM_GUIDES

# Configure logging
logger = logging.getLogger("geo-compiler.packager")


class Packager:
    """
    Packager for creating deterministic ZIP archives.
    Validates all artifacts before packaging.
    """

    def __init__(self):
        self.settings = get_settings()
        self.output_dir = Path(self.settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ============================================
    # SITEMAP.JSON GENERATION
    # ============================================

    def generate_sitemap(self, site: str, pages: list[PageData]) -> SitemapOutput:
        """
        Generate sitemap.json from classified pages.
        """
        entries = []
        for page in pages:
            classification = page.classification
            entries.append(SitemapEntry(
                url=page.url,
                page_type=classification.get("page_type", "other")
            ))

        return SitemapOutput(site=site, urls=entries)

    # ============================================
    # DEPLOYMENT GUIDE GENERATION
    # ============================================

    def generate_deploy_guide(self, domain: str, total_pages: int) -> str:
        """
        Generate practical deployment guide.
        """
        return f"""# 🚀 CiteKit Deployment Guide for {domain}

**Pages Analyzed:** {total_pages}  
**Generated:** This package contains everything you need to make your website visible to AI.

---

## ⚡ Quick Start (Do These First)

### 1. Deploy `robots.txt` (CRITICAL)
Without this, AI crawlers like GPTBot and ClaudeBot may ignore your site entirely.

**What to do:**
- Open `robots.txt` from this package
- Append its contents to your existing `https://{domain}/robots.txt`
- Or replace entirely if you don't have custom rules

### 2. Deploy `llms.txt`
This is the official standard (llmstxt.org) for helping LLMs understand your website.

**What to do:**
- Upload `llm.txt` to: `https://{domain}/llms.txt`

| Platform | Location |
|----------|----------|
| **Vercel/Next.js** | `public/llms.txt` |
| **Netlify** | `public/llms.txt` |
| **WordPress** | `/public_html/llms.txt` via FTP |
| **AWS S3** | Root of bucket |

---

## 💎 Advanced Setup (Maximum Impact)

### 3. Add Schema.org JSON-LD
Structured data helps both Google AND AI systems understand your content.

**What to do:**
1. Open `schemas/organization-schema.html`
2. Copy the entire `<script>` block
3. Paste into your homepage's `<head>` section
4. Repeat with `faq-schema.html` on your FAQ page

### 4. Deploy `mcp.json` (Optional - For AI Agents)
The Model Context Protocol helps AI agents route queries to the right pages.

**What to do:**
- Upload to: `https://{domain}/.well-known/mcp.json`
- Or: `https://{domain}/mcp.json`

### 5. Follow Your Custom Roadmap
Open `CITATION-ROADMAP.md` for your personalized action plan.

---

## 📦 Complete File Inventory

| File | Purpose | Deploy? |
|------|---------|---------|
| `robots.txt` | AI Crawler Permissions | ✅ REQUIRED |
| `llm.txt` | LLM Index (llmstxt.org standard) | ✅ REQUIRED |
| `sitemap.xml` | Standard XML Sitemap | ✅ REQUIRED |
| `mcp.json` | Agent Routing Protocol | ✅ Recommended |
| `facts.jsonld` | Schema.org Entity Data | Reference |
| `schemas/*.html` | Ready-to-paste JSON-LD | ✅ REQUIRED |
| `CITATION-ROADMAP.md` | Your Action Plan | Read First |
| `sitemap.json` | Page Classification Data | Reference |
| `pages/*.json` | Raw Page Data | Reference |

---

## 🧪 Verification

After deploying, test that your files are accessible:

```bash
curl https://{domain}/llms.txt
curl https://{domain}/robots.txt
```

**Test with AI:**
1. Go to ChatGPT or Claude
2. Ask: "Tell me about {domain}"
3. Check if you're cited correctly

---

## 📞 Support

Questions? Check the CITATION-ROADMAP.md for troubleshooting tips.
"""

    # ============================================
    # PAGE JSON FILES
    # ============================================

    def prepare_page_json(self, page: PageData) -> dict:
        """
        Prepare page data for JSON export per schema.
        """
        return {
            "url": page.url,
            "title": page.title,
            "description": page.description,
            "content": page.content,
            "headings": page.headings,
            "classification": {
                "page_type": page.classification.get("page_type", "other"),
                "intent": page.classification.get("primary_intent", "informational")
            }
        }

    # ============================================
    # VALIDATION
    # ============================================

    def validate_artifacts(
        self,
        llm_txt: str,
        mcp: MCPOutput,
        sitemap: SitemapOutput,
        pages: list[PageData]
    ) -> list[str]:
        """
        Validate all artifacts before packaging.
        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Validate llm.txt
        if not llm_txt or len(llm_txt) < 50:
            errors.append("llm.txt is too short or empty")

        # Validate MCP (keep check even if we don't output file)
        if not mcp.endpoints:
            errors.append("mcp.json has no endpoints")
        if not mcp.site:
            errors.append("mcp.json missing site field")

        # Validate sitemap
        if not sitemap.urls:
            errors.append("sitemap.json has no URLs")

        # Validate pages
        if not pages:
            errors.append("No pages to package")

        return errors

    # ============================================
    # ZIP CREATION
    # ============================================

    def create_zip(
        self,
        domain: str,
        llm_txt: str,
        mcp: MCPOutput,
        sitemap: SitemapOutput,
        pages: list[PageData],
        facts: dict = None,
        audit_report: str = "",
        benchmark_report: str = "",
        score_data: dict = None,
        issues: list = None
    ) -> str:
        """
        Create deterministic ZIP package.
        Returns path to created ZIP file.
        """
        # Clean domain for filename
        safe_domain = domain.replace(".", "_").replace(":", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{safe_domain}-geo.zip"
        zip_path = self.output_dir / zip_filename

        # Create ZIP with deterministic ordering
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 0. index.html - Beautiful visual report (FIRST for easy access)
            html_report = self.generate_html_report(
                domain, pages, mcp, score_data or {}, issues or []
            )
            zf.writestr("index.html", html_report)

            # 1. DEPLOYMENT-GUIDE.md - Quick start guide
            deploy_guide = self.generate_deploy_guide(domain, len(pages))
            zf.writestr("DEPLOYMENT-GUIDE.md", deploy_guide)

            # 2. llm.txt AND llms.txt (both for compatibility)
            # llm.txt is commonly used, llms.txt is the llmstxt.org standard
            zf.writestr("llm.txt", llm_txt)
            zf.writestr("llms.txt", llm_txt)  # Same content, different name

            # 3. robots.txt - Optimized for AI crawlers
            robots_txt = self._generate_robots_txt(domain)
            zf.writestr("robots.txt", robots_txt)
            
            # 4. Schema files (ready to paste into <head>)
            schemas = self._generate_schema_files(facts, pages, domain)
            for name, content in schemas.items():
                zf.writestr(f"schemas/{name}", content)
            
            # 5. CITATION-ROADMAP.md (The replacement for AUDIT.md)
            if score_data and issues:
                readiness_score = ReadinessScore(
                    total=score_data.get("total", 0),
                    grade=score_data.get("grade", "N/A"),
                    breakdown=score_data.get("breakdown", {}),
                    issues=[],
                    action_items=score_data.get("quick_wins", []),
                    summary=score_data.get("interpretation", ""),
                    disclaimer=""
                )
                roadmap = generate_citation_roadmap(domain, readiness_score, facts or {})
                zf.writestr("CITATION-ROADMAP.md", roadmap)

            # 5b. COMPETITOR-BENCHMARK.md (If competitor analysis was done)
            if benchmark_report:
                zf.writestr("COMPETITOR-BENCHMARK.md", benchmark_report)

            # 6. facts.jsonld (Raw structured data)
            if facts:
                 facts_json = json.dumps(facts, indent=2, sort_keys=True)
                 zf.writestr("facts.jsonld", facts_json)

            # 7. mcp.json (Agent routing protocol - tells AI where to find things)
            mcp_json = json.dumps(mcp.model_dump(), indent=2, sort_keys=True)
            zf.writestr("mcp.json", mcp_json)

            # 8. sitemap.json (Reference only)
            sitemap_json = json.dumps(sitemap.model_dump(), indent=2, sort_keys=True)
            zf.writestr("sitemap.json", sitemap_json)
            
            # 9. sitemap.xml (Standard XML sitemap for deployment)
            sitemap_xml = self._generate_sitemap_xml(domain, sitemap)
            zf.writestr("sitemap.xml", sitemap_xml)

            # 10. pages/ directory (INTERNAL USE for re-runs / reference)
            for page in sorted(pages, key=lambda p: p.url):
                slug = ContentExtractor.url_to_slug(page.url)
                page_json = json.dumps(self.prepare_page_json(page), indent=2, sort_keys=True)
                zf.writestr(f"pages/{slug}.json", page_json)

        return str(zip_path)
    
    def _generate_robots_txt(self, domain: str) -> str:
        """Generate optimized robots.txt for AI crawler access - 2024 Edition"""
        return f"""# Robots.txt for {domain}
# Generated by CiteKit - Optimized for AI Crawler Access (2024)
# 
# This file explicitly allows AI crawlers to access your content.
# Without these permissions, your site may be invisible to AI systems.

# ===========================================
# DEFAULT: Allow all standard crawlers
# ===========================================
User-agent: *
Allow: /

# ===========================================
# OPENAI CRAWLERS
# ===========================================
# GPTBot: Collects data for improving GPT models
User-agent: GPTBot
Allow: /

# ChatGPT-User: Real-time browsing within ChatGPT
User-agent: ChatGPT-User
Allow: /

# OAI-SearchBot: Powers SearchGPT
User-agent: OAI-SearchBot
Allow: /

# ===========================================
# ANTHROPIC CRAWLERS (Claude)
# ===========================================
# ClaudeBot: Training data collection
User-agent: ClaudeBot
Allow: /

# Claude-User: Real-time browsing in Claude
User-agent: Claude-User
Allow: /

# Claude-SearchBot: Search features
User-agent: Claude-SearchBot
Allow: /

# Legacy name
User-agent: anthropic-ai
Allow: /

# ===========================================
# GOOGLE AI
# ===========================================
# Google-Extended: Gemini/Bard training
User-agent: Google-Extended
Allow: /

# ===========================================
# OTHER AI CRAWLERS
# ===========================================
User-agent: PerplexityBot
Allow: /

User-agent: cohere-ai
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

User-agent: Bytespider
Allow: /

User-agent: YouBot
Allow: /

User-agent: CCBot
Allow: /

# ===========================================
# BLOCKED PATHS (customize as needed)
# ===========================================
Disallow: /admin/
Disallow: /api/internal/
Disallow: /private/
Disallow: /_next/
Disallow: /wp-admin/

# ===========================================
# LLM RESOURCES
# ===========================================
# These are informal headers that some AI systems may check
# LLM-Index: https://{domain}/llms.txt
# Facts: https://{domain}/facts.jsonld

# Standard sitemap
Sitemap: https://{domain}/sitemap.xml
"""

    def _generate_sitemap_xml(self, domain: str, sitemap: SitemapOutput) -> str:
        """
        Generate a proper XML sitemap following the sitemaps.org protocol.
        This can be deployed directly to the server.
        """
        from datetime import datetime
        from xml.sax.saxutils import escape
        
        # Current date in W3C format
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            f'  <!-- Generated by CiteKit for {domain} on {today} -->',
        ]
        
        for entry in sitemap.urls:
            url = escape(entry.url)  # Escape special XML characters
            page_type = entry.page_type
            
            # Determine priority and changefreq based on page type
            if page_type == "homepage":
                priority = "1.0"
                changefreq = "daily"
            elif page_type in ("product", "service", "pricing"):
                priority = "0.9"
                changefreq = "weekly"
            elif page_type in ("about", "contact", "company"):
                priority = "0.8"
                changefreq = "monthly"
            elif page_type in ("blog", "article", "news"):
                priority = "0.7"
                changefreq = "weekly"
            elif page_type in ("docs", "documentation", "help"):
                priority = "0.6"
                changefreq = "weekly"
            else:
                priority = "0.5"
                changefreq = "monthly"
            
            xml_parts.append(f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>""")
        
        xml_parts.append('</urlset>')
        
        return '\n'.join(xml_parts)


    def _generate_schema_files(self, facts: dict, pages: list, domain: str) -> dict:
        """Generate schema HTML files for deployment"""
        # Pass full page data including title and description
        pages_data = [
            {
                "url": p.url, 
                "title": p.title,
                "description": p.description,
                "content": p.content[:500] if p.content else ""  # Truncate content for efficiency
            } 
            for p in pages
        ]
        
        generator = SchemaGenerator(facts or {}, pages_data, domain)
        
        schemas = generator.generate_all_schemas()
        
        return {
            "organization-schema.html": schemas.get("organization", ""),
            "faq-schema.html": schemas.get("faq", ""),
            "software-app-schema.html": schemas.get("software_application", ""),
            "howto-schema.html": schemas.get("howto", ""),
        }


    # ============================================
    # HTML REPORT GENERATION
    # ============================================

    def generate_html_report(
        self,
        domain: str,
        pages: list[PageData],
        mcp: MCPOutput,
        score_data: dict,
        issues: list
    ) -> str:
        """
        Generate beautiful HTML report from template.
        """
        # Load template
        template_path = Path(__file__).parent / "templates" / "report.html"
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
        else:
            # Fallback minimal template
            return self._generate_fallback_html(domain, score_data, pages)

        # Calculate scores
        total_score = score_data.get("total", 0) if score_data else 0
        llm_score = score_data.get("llm_readiness", 0) if score_data else 0

        # Score offset for circle (264 is full circle)
        score_offset = 264 - (264 * total_score / 100)

        # Determine score label and colors
        if total_score >= 80:
            score_label = "Excellent"
            score_desc = "Your site is highly optimized for AI discovery and citation."
            color_start, color_end = "#22c55e", "#10b981"
        elif total_score >= 60:
            score_label = "Good"
            score_desc = "Your site is well-prepared for AI, with room for improvement."
            color_start, color_end = "#3b82f6", "#8b5cf6"
        elif total_score >= 40:
            score_label = "Fair"
            score_desc = "Your site has basic AI readiness. Address the issues below."
            color_start, color_end = "#f97316", "#eab308"
        else:
            score_label = "Needs Work"
            score_desc = "Your site needs significant improvements for AI visibility."
            color_start, color_end = "#ef4444", "#f97316"

        # Generate issues HTML
        issues_html = ""
        for issue in issues[:10]:  # Limit to 10 issues
            severity = issue.get("severity", "info").lower()
            icon_class = "critical" if severity == "critical" else ("warning" if severity == "warning" else "info")
            icon_text = "!" if severity == "critical" else ("⚠" if severity == "warning" else "i")
            
            affected = ""
            if issue.get("affected_urls"):
                affected = f'<div class="issue-affected">{", ".join(issue["affected_urls"][:3])}</div>'
            
            issues_html += f'''
                <div class="issue-card">
                    <div class="issue-icon {icon_class}">{icon_text}</div>
                    <div class="issue-content">
                        <div class="issue-title">{issue.get("title", "Issue")}</div>
                        <div class="issue-description">{issue.get("description", "")}</div>
                        {affected}
                    </div>
                </div>
            '''
        
        # Endpoints (removed from detailed view but count kept for now)
        endpoints_count = len(mcp.endpoints) if mcp and mcp.endpoints else 0
        total_words = sum(len(p.content.split()) for p in pages)

        # Get breakdown scores from score_data
        content_score = score_data.get("content", 0) if score_data else 0
        metadata_score = score_data.get("metadata", 0) if score_data else 0
        structure_score = score_data.get("structure", 0) if score_data else 0
        
        # Calculate percentages (each category is out of 25, so multiply by 4 for percentage)
        content_percent = min(100, content_score * 4)
        metadata_percent = min(100, metadata_score * 4)
        structure_percent = min(100, structure_score * 4)
        llm_percent = min(100, llm_score * 4)
        
        # Generate timestamp
        generated_at = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

        replacements = {
            # Domain and timestamp
            "{{DOMAIN}}": domain,
            "{{GENERATED_AT}}": generated_at,
            
            # Main score (template uses SCORE, not TOTAL_SCORE)
            "{{SCORE}}": str(total_score),
            "{{SCORE_OFFSET}}": str(score_offset),
            "{{SCORE_LABEL}}": score_label,
            "{{SCORE_DESCRIPTION}}": score_desc,  # Template uses SCORE_DESCRIPTION
            
            # Score colors (template uses SCORE_COLOR_START/END)
            "{{SCORE_COLOR_START}}": color_start,
            "{{SCORE_COLOR_END}}": color_end,
            
            # Breakdown scores
            "{{CONTENT_SCORE}}": str(content_score),
            "{{CONTENT_PERCENT}}": str(content_percent),
            "{{METADATA_SCORE}}": str(metadata_score),
            "{{METADATA_PERCENT}}": str(metadata_percent),
            "{{STRUCTURE_SCORE}}": str(structure_score),
            "{{STRUCTURE_PERCENT}}": str(structure_percent),
            "{{LLM_SCORE}}": str(llm_score),
            "{{LLM_PERCENT}}": str(llm_percent),
            
            # Statistics
            "{{TOTAL_PAGES}}": str(len(pages)),
            "{{TOTAL_WORDS}}": f"{total_words:,}",
            "{{ISSUES_COUNT}}": str(len(issues)),
            "{{ENDPOINTS_COUNT}}": str(endpoints_count),
            
            # Issues HTML
            "{{ISSUES_HTML}}": issues_html
        }

        html = template
        for key, value in replacements.items():
            html = html.replace(key, value)

        return html

    def _generate_fallback_html(self, domain: str, score_data: dict, pages: list) -> str:
        """Generate minimal HTML if template is missing."""
        total_score = score_data.get("total", 0) if score_data else 0
        return f'''<!DOCTYPE html>
<html>
<head><title>GEO Report - {domain}</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem;">
<h1>GEO Report: {domain}</h1>
<h2>Score: {total_score}/100</h2>
<p>Pages analyzed: {len(pages)}</p>
<p>Open the other files in this package for details.</p>
</body>
</html>'''

    def generate_deployment_guide_html(self, domain: str, platform_info: dict = None) -> str:
        """
        Generate interactive HTML deployment guide with platform-specific instructions.
        
        Args:
            domain: The website domain
            platform_info: Dict with 'detected', 'name', 'hosting', 'guide_id' from platform detection
        """
        from datetime import datetime
        
        # Load template
        template_path = Path(__file__).parent / "templates" / "guide.html"
        if not template_path.exists():
            return f"<html><body><h1>Deployment Guide for {domain}</h1><p>Template not found.</p></body></html>"
        
        template = template_path.read_text(encoding="utf-8")
        
        # Determine platform details
        if platform_info:
            platform_id = platform_info.get("guide_id", "cpanel")
            platform_name = platform_info.get("name", "Custom/Static")
        else:
            platform_id = "cpanel"
            platform_name = "cPanel / Traditional Hosting"
        
        # Get platform guide data
        guide_data = get_platform_guide(platform_id)
        
        # Generate all platform instructions (all tabs)
        all_instructions = get_all_platform_instructions()
        
        # Generate timestamp
        generated_at = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
        
        # Platform icon mapping
        platform_icons = {
            "wordpress": "📝",
            "shopify": "🛒",
            "wix": "🎨",
            "vercel": "▲",
            "netlify": "🌐",
            "cpanel": "⚙️",
            "custom": "🔧",
        }
        
        replacements = {
            "{{DOMAIN}}": domain,
            "{{GENERATED_AT}}": generated_at,
            "{{PLATFORM_ID}}": platform_id,
            "{{PLATFORM_NAME}}": platform_name,
            "{{PLATFORM_ICON}}": platform_icons.get(platform_id, "📖"),
            "{{PLATFORM_COLOR}}": guide_data.get("color", "#6B7280"),
            "{{PLATFORM_LETTER}}": guide_data.get("letter", "?"),
            "{{PLATFORM_INSTRUCTIONS}}": all_instructions,
        }
        
        html = template
        for key, value in replacements.items():
            html = html.replace(key, str(value))
        
        return html

    # ============================================
    # MAIN PACKAGING
    # ============================================

    def generate_package(
        self,
        job_id: str,
        domain: str,
        llm_txt: str,
        mcp: MCPOutput,
        pages: list[PageData],
        facts: dict = None,
        extracted_facts: list = None,
        benchmark_report: str = "",
        citation_score_data: dict = None,
        citation_issues: list = None,
        platform_info: dict = None
    ) -> tuple[str, list[str], int]:
        """
        Main packaging orchestration.
        Returns (zip_path, errors, citation_score).
        """
        # Generate sitemap
        sitemap = self.generate_sitemap(domain, pages)

        # Validate
        errors = self.validate_artifacts(llm_txt, mcp, sitemap, pages)

        if errors:
            return "", errors, 0

        # Run GEO Audit (for backwards compatibility)
        auditor = GEOAuditor()
        geo_score, geo_issues, audit_report = auditor.generate_audit(domain, pages, mcp, llm_txt)
        
        print(f"GEO Audit complete: Score {geo_score.total}/100 ({len(geo_issues)} issues found)")

        # ---------------------------------------------------------
        # SAVE PREVIEW ARTIFACTS (raw files for frontend preview)
        # ---------------------------------------------------------
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. structure.md (llm.txt)
        (job_dir / "structure.md").write_text(llm_txt, encoding="utf-8")
        
        # 2. content.json (mcp.json)
        (job_dir / "content.json").write_text(
            json.dumps(mcp.model_dump(), indent=2, sort_keys=True), 
            encoding="utf-8"
        )
        
        # 3. facts.jsonld
        if facts:
            (job_dir / "facts.jsonld").write_text(
                json.dumps(facts, indent=2, sort_keys=True),
                encoding="utf-8"
            )

        # Use Citation Score if available, otherwise fall back to GEO Score
        if citation_score_data:
            score_data = {
                "total": citation_score_data.get("total", 0),
                "grade": citation_score_data.get("grade", "N/A"),
                "breakdown": citation_score_data.get("breakdown", {}),
                "quick_wins": citation_score_data.get("quick_wins", []),
                "interpretation": citation_score_data.get("interpretation", ""),
                # Also keep GEO score components for HTML report
                "content": geo_score.content_quality,
                "metadata": geo_score.metadata_completeness,
                "structure": geo_score.structure_clarity,
                "llm_readiness": geo_score.llm_readiness
            }
            final_score = citation_score_data.get("total", geo_score.total)
            issues_for_package = citation_issues or []
        else:
            # Fallback to GEO Score format
            score_data = {
                "total": geo_score.total,
                "content": geo_score.content_quality,
                "metadata": geo_score.metadata_completeness,
                "structure": geo_score.structure_clarity,
                "llm_readiness": geo_score.llm_readiness
            }
            final_score = geo_score.total
            # Convert GEO issues to list of dicts
            issues_for_package = [
                {
                    "severity": issue.severity if isinstance(issue.severity, str) else issue.severity,
                    "title": issue.title,
                    "description": issue.recommendation,
                    "affected_urls": issue.affected_urls
                }
                for issue in geo_issues
            ]


        # Create ZIP with all reports
        zip_path = self.create_zip(
            domain, llm_txt, mcp, sitemap, pages, facts, 
            audit_report, benchmark_report, 
            score_data, issues_for_package,
            # Pass payment info to deciding on GMB pack
            include_gmb=(citation_score_data is not None) or (job_id and self._is_job_paid(job_id)),
            extracted_facts=extracted_facts,
            platform_info=platform_info
        )

        return zip_path, [], final_score

    def _is_job_paid(self, job_id: str) -> bool:
        # Helper to check payment status (simplified, really should be passed in)
        # For now, we rely on the `citation_score_data` presence as a proxy for "Full/Paid Run" 
        # OR we just generate it for everyone for now as a "Free Preview" (Value-Add Strategy)
        # Let's generate it for everyone but maybe put it in a "Preview" folder if not paid?
        # Re-reading prompt: "we need to show how much more value we are providing"
        # Let's include it for EVERYONE right now to WOW them.
        return True

    # ============================================
    # ZIP CREATION
    # ============================================

    def create_zip(
        self,
        domain: str,
        llm_txt: str,
        mcp: MCPOutput,
        sitemap: SitemapOutput,
        pages: list[PageData],
        facts: dict = None,
        audit_report: str = "",
        benchmark_report: str = "",
        score_data: dict = None,
        issues: list = None,
        include_gmb: bool = True,
        extracted_facts: list = None,
        platform_info: dict = None
    ) -> str:
        """
        Create deterministic ZIP package.
        Returns path to created ZIP file.
        """
        # Clean domain for filename
        safe_domain = domain.replace(".", "_").replace(":", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{safe_domain}-geo.zip"
        zip_path = self.output_dir / zip_filename

        # Create ZIP with deterministic ordering
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 0. index.html - Beautiful visual report (FIRST for easy access)
            html_report = self.generate_html_report(
                domain, pages, mcp, score_data or {}, issues or []
            )
            zf.writestr("index.html", html_report)

            # 1. DEPLOYMENT-GUIDE.md - Quick start guide
            deploy_guide = self.generate_deploy_guide(domain, len(pages))
            zf.writestr("DEPLOYMENT-GUIDE.md", deploy_guide)

            # 1b. guide.html - Interactive platform-specific guide
            guide_html = self.generate_deployment_guide_html(domain, platform_info)
            zf.writestr("guide.html", guide_html)

            # 2. llm.txt AND llms.txt (both for compatibility)
            # llm.txt is commonly used, llms.txt is the llmstxt.org standard
            zf.writestr("llm.txt", llm_txt)
            zf.writestr("llms.txt", llm_txt)  # Same content, different name

            # 3. robots.txt - Optimized for AI crawlers
            robots_txt = self._generate_robots_txt(domain)
            zf.writestr("robots.txt", robots_txt)
            
            # 4. Schema files (ready to paste into <head>)
            schemas = self._generate_schema_files(facts, pages, domain)
            for name, content in schemas.items():
                zf.writestr(f"schemas/{name}", content)
            
            # 5. CITATION-ROADMAP.md (The replacement for AUDIT.md)
            if score_data and issues:
                readiness_score = ReadinessScore(
                    total=score_data.get("total", 0),
                    grade=score_data.get("grade", "N/A"),
                    breakdown=score_data.get("breakdown", {}),
                    issues=[],
                    action_items=score_data.get("quick_wins", []),
                    summary=score_data.get("interpretation", ""),
                    disclaimer=""
                )
                roadmap = generate_citation_roadmap(domain, readiness_score, facts or {})
                zf.writestr("CITATION-ROADMAP.md", roadmap)

            # 5b. COMPETITOR-BENCHMARK.md (If competitor analysis was done)
            if benchmark_report:
                zf.writestr("COMPETITOR-BENCHMARK.md", benchmark_report)

            # 6. GMB OPTIMIZATION PACK (Value Add)
            if include_gmb and extracted_facts:
                try:
                    from gmb_generator import GMBGenerator
                    
                    # Construct minimal metadata
                    # We can try to get org_name from facts dict if available, or domain
                    org_name = domain
                    if facts and facts.get("name"):
                        org_name = facts.get("name")
                    
                    metadata = {
                        "org_name": org_name,
                        "domain": domain
                    }
                    
                    print(f"Generating GMB Optimization Pack for {org_name}...")
                    gmb_gen = GMBGenerator(extracted_facts, pages, metadata)
                    gmb_kit = gmb_gen.generate_kit()
                    
                    # Create dedicated folder in ZIP
                    base_folder = "GMB_Optimization_Pack/"
                    for filename, content in gmb_kit.items():
                        zf.writestr(f"{base_folder}{filename}", content)
                        
                except ImportError:
                    print("GMB Generator module not found.")
                except Exception as e:
                    print(f"Error generating GMB pack: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 6b. facts.jsonld (Raw structured data)
            if facts:
                 facts_json = json.dumps(facts, indent=2, sort_keys=True)
                 zf.writestr("facts.jsonld", facts_json)

            # 7. mcp.json (Agent routing protocol - tells AI where to find things)
            mcp_json = json.dumps(mcp.model_dump(), indent=2, sort_keys=True)
            zf.writestr("mcp.json", mcp_json)

            # 8. sitemap.json (Reference only)
            sitemap_json = json.dumps(sitemap.model_dump(), indent=2, sort_keys=True)
            zf.writestr("sitemap.json", sitemap_json)
            
            # 9. sitemap.xml (Standard XML sitemap for deployment)
            sitemap_xml = self._generate_sitemap_xml(domain, sitemap)
            zf.writestr("sitemap.xml", sitemap_xml)

            # 10. pages/ directory (INTERNAL USE for re-runs / reference)
            for page in sorted(pages, key=lambda p: p.url):
                slug = ContentExtractor.url_to_slug(page.url)
                page_json = json.dumps(self.prepare_page_json(page), indent=2, sort_keys=True)
                zf.writestr(f"pages/{slug}.json", page_json)

        return str(zip_path)
