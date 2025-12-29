"""
CiteKit - Knowledge Synthesizer (v2)
Elite-tier LLM.txt and MCP JSON generation using Gemini
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


import google.generativeai as genai

from config import get_settings
from models import PageData, MCPOutput, MCPEndpoint, MCPPriority

# Configure logging
logger = logging.getLogger("geo-compiler.synthesizer")


class KnowledgeSynthesizer:
    """
    World-class knowledge synthesis using Gemini.
    Generates llm.txt and MCP JSON from classified page data.
    """

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.temperature = settings.llm_temperature

    # ============================================
    # LLM.TXT GENERATION - ELITE PROMPTS
    # ============================================

    MAX_CONTEXT_PAGES = 50

    # ============================================
    # ELITE LLM.TXT PROMPTS
    # Based on: llmstxt.org spec, Stripe implementation, Princeton GEO research
    # ============================================
    
    LLM_TXT_SYSTEM = """You are a specialized Knowledge Engineer optimizing content for AI Agents (RAG).
Your goal is to convert unstructured website content into a high-density, machine-readable Markdown format (/llms.txt).

## CRITICAL PRINCIPLES
1. **Information Density:** maximizing facts per token.
2. **Structure:** AI agents need URL patterns and Glossaries to navigate.
3. **No Fluff:** Remove all marketing language ("cutting-edge", "best-in-class", "solutions provider").
4. **Accuracy:** Never hallucinate stats or URLs.
5. **Adaptability:** Adapt the output structure to the type of website (E-commerce vs SaaS vs Blog).

## OUTPUT QUALITY CHECKS
- Does the "Key Data" section contain actual numbers/metrics? (If not, omit it).
- Does the "Terminology" section define domain-specific jargon? (If not, omit it).
- Are the URL patterns strictly derived from the input list?
"""

    LLM_TXT_USER_TEMPLATE = """# TASK
Generate a world-class /llms.txt for **{site}**.

# INPUT DATA ({total_pages} analyzed pages)
{page_summaries}

# REQUIRED MARKDOWN STRUCTURE
(Strictly follow this high-density layout. Omit sections if data is missing.)

# [Project Name]

> [One-sentence mission statement / summary]

# Key Data
- [Metric Name]: [Value]
(Extract specific numbers: e.g. "Pricing", "Year Founded", "User Count", "SKU Count")
(If no metrics found, omit this section)

# Core Documentation
- [Page Title](URL): [When should an Agent cite this?]

# Data Structure / URL Patterns
(Analyze the input URLs to find structural patterns. Examples of what to look for:)
- **Resources:** `/blog/{{slug}}`, `/product/{{id}}`, `/docs/{{section}}`
(If no consistent patterns exist, omit this section)

# Terminology
(Define domain-specific acronyms or jargon found in the content)
- **[Term]:** [Definition]
- **[Term]:** [Definition]

## Features / Services
- [Page Title](URL): [Description]

# RULES
1. **Precision:** Use ONLY URLs provided in the input.
2. **Glossary:** Extract definitions for acronyms (e.g., "SaaS", "API", "ROI").
3. **Structure:** Group related links logically.
4. **Output:** Return ONLY the Markdown content.
"""

    async def generate_llm_txt(self, site: str, pages: list[PageData]) -> str:
        """
        Generate world-class llm.txt from classified page data.
        """
        # Sort pages by importance (homepage first, then key pages)
        sorted_pages = sorted(
            pages, 
            key=lambda p: (
                p.url != f"https://{site}" and p.url != f"https://www.{site}",
                "pricing" not in p.url.lower(),
                "docs" not in p.url.lower(),
                "api" not in p.url.lower(),
                "about" not in p.url.lower(),
                "contact" not in p.url.lower(),
                len(p.url),
            )
        )

        # Build rich page summaries with more context
        summaries = []
        for page in sorted_pages[:self.MAX_CONTEXT_PAGES]:
            c = page.classification
            page_type = c.get('page_type', 'page')
            
            # Include rich content context (cleaned by Trafilatura)
            content_snippet = ""
            if page.content:
                # Get first 15k chars for richer context
                content_snippet = page.content[:15000].replace('\n', ' ').strip()
            
            summary = f"""[{page_type.upper()}] {page.url}
  Title: "{page.title}"
  Description: {page.description[:200] if page.description else 'N/A'}
  Topics: {', '.join(c.get('topics', [])[:5])}
  Content Preview: {content_snippet}..."""
            summaries.append(summary)

        # Simple, clean prompt - let the LLM do the work
        prompt = self.LLM_TXT_USER_TEMPLATE.format(
            site=site,
            total_pages=len(pages),
            page_summaries="\n\n".join(summaries)
        )

        try:
            print(f"[Synthesizer] Generating elite llm.txt for {site}...")
            response = self.model.generate_content(
                [self.LLM_TXT_SYSTEM, prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.15,  # Very low for maximum factual accuracy
                    max_output_tokens=8000,  # Increased for comprehensive output
                    top_p=0.9
                )
            )
            
            if not response.parts:
                raise ValueError("Gemini returned empty response")

            result = response.text.strip()
            
            # Clean up any markdown code blocks if present
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            print(f"[Synthesizer] llm.txt generation successful ({len(result)} chars)")
            return result

        except Exception as e:
            print(f"[Synthesizer] CRITICAL ERROR: {e}")
            return self._generate_fallback_llm_txt(site, pages, str(e))

    def _generate_fallback_llm_txt(self, site: str, pages: list[PageData], error: str) -> str:
        """Generate a structured fallback when LLM fails."""
        page_list = "\n".join([f"- [{p.title}]({p.url})" for p in pages[:20]])
        
        return f"""# {site.upper()}

> Identity document for {site}

## STATUS
⚠️ **PARTIAL GENERATION** - LLM synthesis encountered an error.

Error: `{error}`

## AVAILABLE DATA

This package contains extracted data from **{len(pages)}** pages.

### Indexed Pages
{page_list}

## RECOMMENDED ACTION
- Review `pages/*.json` for raw structured content
- Re-run compilation if this error persists
- Check API key configuration if model errors occur

---
*Generated by CiteKit (Fallback Mode)*
"""

    # ============================================
    # ELITE MCP JSON PROMPTS
    # Based on Anthropic's Model Context Protocol specification
    # ============================================

    MCP_SYSTEM = """You are an expert in creating agent routing configurations based on the Model Context Protocol (MCP).

## PURPOSE OF MCP
MCP enables AI agents to understand which URL to visit based on user intent. When a user asks ChatGPT or Claude a question, the AI may browse the web - your MCP file tells it exactly where to go.

## QUALITY REQUIREMENTS
- The "use_when" field is CRITICAL - it must describe specific user queries/intents
- Include example questions that would trigger routing to this page
- Priorities must reflect actual page importance
- Only use URLs from the provided data
- Output VALID JSON only (no markdown code blocks)

## USE_WHEN BEST PRACTICES
Good: "User asks about pricing, costs, subscription plans, or 'how much does X cost'"
Bad: "Pricing page"

Good: "User wants to get started, create account, sign up, or asks 'how do I begin'"  
Bad: "Getting started page"

The use_when should be written as if you're completing: "Route here when the..."
"""

    MCP_USER_TEMPLATE = """Create MCP routing configuration for {site}.

## Page Data
{page_data}

## Output Format
Generate this exact JSON structure (no markdown, just JSON):

{{
  "site": "{site}",
  "generated_at": "{timestamp}",
  "version": "1.0",
  "description": "Routing configuration for AI agents browsing {site}",
  "endpoints": [
    {{
      "url": "https://...",
      "description": "What information this page contains",
      "use_when": "User asks about X, wants to Y, or queries like 'example question'",
      "topics": ["keyword1", "keyword2", "keyword3"],
      "priority": "critical|high|medium|low"
    }}
  ]
}}

## Priority Guide
- critical: Homepage, main product page, pricing (max 3 pages)
- high: Docs home, features, API, getting started (max 5 pages)
- medium: Tutorials, blog posts, case studies
- low: Legal pages, old content, support articles

Generate routing for the 15-20 most important pages only."""

    async def generate_mcp_json(self, site: str, pages: list[PageData]) -> MCPOutput:
        """
        Generate MCP JSON from classified page data.
        """
        page_entries = []
        for page in pages[:50]:
            c = page.classification
            entry = f"URL: {page.url}\nTitle: {page.title}\nType: {c.get('page_type', 'unknown')}\nIntent: {c.get('primary_intent', 'unknown')}\nTopics: {c.get('topics', [])}"
            page_entries.append(entry)

        timestamp = datetime.utcnow().isoformat()
        
        # Extract site name from homepage title
        site_name = site
        site_description = ""
        for page in pages:
            if page.url.rstrip('/') in [f"https://{site}", f"https://www.{site}", f"http://{site}"]:
                site_name = page.title.split(' - ')[0].split(' | ')[0].strip() if page.title else site
                site_description = page.description[:200] if page.description else ""
                break

        prompt = self.MCP_USER_TEMPLATE.format(
            site=site,
            timestamp=timestamp,
            page_data="\n\n".join(page_entries)
        )

        try:
            response = self.model.generate_content(
                [self.MCP_SYSTEM, prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4000
                )
            )

            text = response.text.strip()

            # Clean markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)

            endpoints = []
            for ep in data.get("endpoints", []):
                priority = ep.get("priority", "medium").lower()
                if priority not in ["low", "medium", "high", "critical"]:
                    priority = "medium"

                endpoints.append(MCPEndpoint(
                    url=ep.get("url", ""),
                    description=ep.get("description", ""),
                    use_when=ep.get("use_when", ""),
                    topics=ep.get("topics", []),
                    priority=MCPPriority(priority),
                    content_type=ep.get("content_type", "text/html")
                ))

            return MCPOutput(
                site=site,
                name=site_name,
                description=site_description,
                generated_at=timestamp,
                version="1.0",
                generator="CiteKit",
                llms_txt_url=f"https://{site}/llms.txt",
                facts_jsonld_url=f"https://{site}/facts.jsonld",
                endpoints=endpoints
            )

        except Exception as e:
            print(f"[Synthesizer] MCP generation error: {e}, using fallback")
            return self._generate_fallback_mcp(site, pages)


    def _generate_fallback_mcp(self, site: str, pages: list[PageData]) -> MCPOutput:
        """Generate fallback MCP from page data."""
        timestamp = datetime.utcnow().isoformat()
        endpoints = []
        
        # Extract site name and description from homepage
        site_name = site
        site_description = ""
        for page in pages:
            if page.url.rstrip('/') in [f"https://{site}", f"https://www.{site}", f"http://{site}"]:
                site_name = page.title.split(' - ')[0].split(' | ')[0].strip() if page.title else site
                site_description = page.description[:200] if page.description else ""
                break
        
        for page in pages[:20]:
            c = page.classification
            page_type = c.get("page_type", "other")

            if page_type in ["homepage", "product"]:
                priority = MCPPriority.CRITICAL
            elif page_type in ["pricing", "docs", "documentation", "api"]:
                priority = MCPPriority.HIGH
            elif page_type in ["blog", "about", "support", "guide"]:
                priority = MCPPriority.MEDIUM
            else:
                priority = MCPPriority.LOW

            endpoints.append(MCPEndpoint(
                url=page.url,
                description=page.description or page.title or "Page content",
                use_when=f"When user asks about {page_type}",
                topics=c.get("topics", []),
                priority=priority,
                content_type="text/html"
            ))

        return MCPOutput(
            site=site,
            name=site_name,
            description=site_description,
            generated_at=timestamp,
            version="1.0",
            generator="CiteKit",
            llms_txt_url=f"https://{site}/llms.txt",
            facts_jsonld_url=f"https://{site}/facts.jsonld",
            endpoints=endpoints
        )

    def generate_facts_jsonld(self, pages: list[PageData]) -> dict:
        """
        Generate enhanced facts.jsonld (Schema.org Knowledge Graph)
        
        Implementation based on:
        - Schema.org structured data standards (documented)
        - llmstxt.org specification for LLM-readable content
        - Princeton's GEO research on AI discoverability
        
        Pipeline:
        - 6-step process (NER, Fact Extraction, Entity Linking, Schema, Validation, LLM Enhancement)
        - 5 fact types (statistics, claims, definitions, primary_answer, quotes)
        - 12 validation rules for quality scoring
        
        Best practices included:
        - sameAs links for entity disambiguation (schema.org standard)
        - Statistics and confident statements (research-backed)
        - Proper JSON-LD structure for machine readability
        """
        if not pages:
            return {}

        site = pages[0].url.split('/')[2]
        
        # Extract social profiles (still needed as input to new generator)
        all_content = " ".join([p.content or "" for p in pages[:10]])
        social_links = self._extract_social_profiles(all_content)
        
        # Use new spec-compliant generator
        try:
            from facts_generator import get_facts_generator
            import asyncio
            
            generator = get_facts_generator()
            
            # Run async generator
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    generator.generate(pages, site, social_links)
                )
            finally:
                loop.close()
            
            # Log quality metrics
            print(f"[Synthesizer] facts.jsonld v2 generated:")
            print(f"  - Quality Score: {result['quality_score']}/100")
            print(f"  - Quality Grade: {result['quality_grade']}")
            print(f"  - Facts Extracted: {result['facts_count']}")
            print(f"  - Stats: {result['facts_by_type']}")
            
            return result["facts_jsonld"]
            
        except ImportError as e:
            print(f"[Synthesizer] facts_generator not available: {e}. Path: {os.getcwd()}")
            import traceback
            traceback.print_exc()
            return self._generate_facts_jsonld_fallback(pages, site, social_links)
        except Exception as e:
            print(f"[Synthesizer] facts_generator fatal error: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_facts_jsonld_fallback(pages, site, social_links)
    
    def _generate_facts_jsonld_fallback(self, pages: list[PageData], site: str, social_links: list) -> dict:
        """Fallback facts.jsonld generation (original implementation)."""
        homepage = next((p for p in pages if p.classification.get('page_type') == 'homepage'), pages[0])
        
        # Extract logo URL
        logo_url = self._extract_logo_url(homepage.content or "", site)
        
        # Build base facts
        facts = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": f"https://{site}",
            "url": f"https://{site}",
            "name": self._extract_company_name(homepage),
            "description": homepage.description or "",
        }
        
        if logo_url:
            facts["logo"] = logo_url
        
        # Add sameAs links (CRITICAL for entity disambiguation)
        if social_links:
            facts["sameAs"] = social_links
        
        # Use LLM for deep fact extraction
        facts = self._enhance_facts_with_llm(facts, pages, site)
        
        return facts

    
    def _extract_social_profiles(self, html_content: str) -> list:
        """
        Extract official social media profiles.
        
        sameAs links are a Schema.org standard for entity disambiguation,
        helping AI systems verify the organization's official presence.
        """
        import re
        
        social_patterns = {
            'twitter': r'https?://(?:www\.)?(twitter\.com|x\.com)/([a-zA-Z0-9_]{1,15})(?:/|\?|$|")',
            'linkedin': r'https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9-]+)',
            'facebook': r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)',
            'github': r'https?://(?:www\.)?github\.com/([a-zA-Z0-9-]+)',
            'instagram': r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)',
            'youtube': r'https?://(?:www\.)?youtube\.com/(?:c/|channel/|@)?([a-zA-Z0-9_-]+)',
        }
        
        found_profiles = []
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Handle tuple from capture groups
                username = match[1] if isinstance(match, tuple) else match
                
                # Skip common false positives
                if username.lower() in ['share', 'intent', 'home', 'login', 'signup', 'search']:
                    continue
                
                # Reconstruct clean URL
                if platform == 'twitter':
                    url = f"https://twitter.com/{username}"
                elif platform == 'linkedin':
                    url = f"https://linkedin.com/company/{username}"
                elif platform == 'facebook':
                    url = f"https://facebook.com/{username}"
                elif platform == 'github':
                    url = f"https://github.com/{username}"
                elif platform == 'instagram':
                    url = f"https://instagram.com/{username}"
                elif platform == 'youtube':
                    url = f"https://youtube.com/@{username}"
                else:
                    continue
                
                # Avoid duplicates
                if url not in found_profiles:
                    found_profiles.append(url)
        
        return found_profiles if found_profiles else []
    
    def _extract_logo_url(self, content: str, domain: str) -> str:
        """Extract logo URL from page content"""
        import re
        
        # Look for common logo patterns
        patterns = [
            r'<link[^>]+rel=["\']?(?:icon|shortcut icon|apple-touch-icon)["\']?[^>]+href=["\']?([^"\'>\s]+)',
            r'<img[^>]+(?:class|id)=["\'][^"\']*logo[^"\']*["\'][^>]+src=["\']?([^"\'>\s]+)',
            r'<img[^>]+src=["\']?([^"\'>\s]+)["\']?[^>]+(?:class|id)=["\'][^"\']*logo',
            r'og:image["\'][^>]+content=["\']([^"\']+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                url = match.group(1)
                # Make absolute URL
                if url.startswith('//'):
                    return f"https:{url}"
                elif url.startswith('/'):
                    return f"https://{domain}{url}"
                elif url.startswith('http'):
                    return url
        
        return ""
    
    def _extract_company_name(self, page: PageData) -> str:
        """Extract company name from page data"""
        # Try title first (clean up common suffixes)
        if page.title:
            name = page.title.split('|')[0].split('-')[0].split('–')[0].strip()
            # Remove common suffixes
            for suffix in [' Home', ' Homepage', ' Official', ' Site', ' Website']:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            if name:
                return name
        
        # Fallback to domain
        return page.url.split('/')[2].replace('www.', '').split('.')[0].title()
    
    def _enhance_facts_with_llm(self, facts: dict, pages: list[PageData], site: str) -> dict:
        """Use Gemini to extract deep facts like founder, pricing, founding date"""
        
        # Build context from key pages
        context_parts = []
        
        for page in pages[:15]:
            snippet = f"[{page.classification.get('page_type', 'page')}] {page.title}\n{(page.content or '')[:800]}"
            context_parts.append(snippet)
        
        EXTRACTION_PROMPT = f"""You are a fact extraction expert. Extract ONLY explicitly stated information from the website content.

Website: {site}
Current known facts:
- Name: {facts.get('name', 'Unknown')}
- Description: {facts.get('description', 'Unknown')}

Website content:
{chr(10).join(context_parts)[:8000]}

Extract additional facts in this JSON format. Use null for anything not explicitly stated:

{{
  "foundingDate": "YYYY or null",
  "founder": {{"@type": "Person", "name": "Full Name"}} or null,
  "headquarters": "City, Country" or null,
  "numberOfEmployees": "50-100 or exact number" or null,
  "offers": [
    {{"@type": "Offer", "name": "Plan Name", "price": "numeric price only", "priceCurrency": "USD"}}
  ],
  "slogan": "Company tagline" or null
}}

CRITICAL Rules:
- ONLY extract facts explicitly stated in the content
- For founding date: look for "Founded in YYYY", "Since YYYY", "Est. YYYY", "© YYYY-"
- For founder: look for "Founded by", "CEO:", "Founder:", team pages
- For pricing: Extract ALL visible pricing tiers (Starter, Pro, Enterprise, etc.) with their prices. Look for $XX, $XX/mo, $XX/month patterns.
- Include EVERY pricing tier you can find, not just one
- Return null if not found - NEVER fabricate
"""

        try:
            response = self.model.generate_content(
                EXTRACTION_PROMPT,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            extracted = json.loads(response.text)
            
            # Merge extracted facts
            if extracted.get("foundingDate"):
                facts["foundingDate"] = str(extracted["foundingDate"])
            
            if extracted.get("founder"):
                facts["founder"] = extracted["founder"]
            
            if extracted.get("headquarters"):
                facts["address"] = {
                    "@type": "PostalAddress",
                    "addressLocality": extracted["headquarters"]
                }
            
            if extracted.get("numberOfEmployees"):
                facts["numberOfEmployees"] = {
                    "@type": "QuantitativeValue",
                    "value": extracted["numberOfEmployees"]
                }
            
            if extracted.get("offers"):
                facts["makesOffer"] = extracted["offers"]
            
            if extracted.get("slogan"):
                facts["slogan"] = extracted["slogan"]
            
            print(f"[Synthesizer] Enhanced facts extraction complete")
            
        except Exception as e:
            print(f"[Synthesizer] Deep extraction failed: {e}")
        
        return facts

