"""
Schema Generator Module

Generates ready-to-paste HTML schema snippets for common page types.

What we know:
- Schema.org is the official web standard for structured data
- Google uses JSON-LD for rich snippets (documented)
- OpenAI's GPTBot crawls websites (documented)

What we DON'T know:
- Whether ChatGPT/Claude use JSON-LD in responses
- Exact "citation multiplier" from structured data
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger("geo-compiler.schema_generator")


class SchemaGenerator:
    """Generate Schema.org markup for different page types"""
    
    def __init__(self, facts: Dict, pages_data: List[Dict], domain: str):
        self.facts = facts or {}
        self.pages = pages_data or []
        self.domain = domain
        
        # Extract data from pages if facts is empty
        self._ensure_basic_facts()
    
    def _ensure_basic_facts(self):
        """Extract basic facts from pages if not present in facts dict"""
        # Try to get name from homepage title
        if not self.facts.get("name"):
            for page in self.pages:
                url = page.get("url", "")
                if any(url.rstrip('/').endswith(x) for x in [self.domain, f"www.{self.domain}"]):
                    title = page.get("title", "")
                    if title:
                        # Extract company name from title (before " - " or " | ")
                        name = title.split(" - ")[0].split(" | ")[0].strip()
                        if name:
                            self.facts["name"] = name
                    break
        
        # Use domain as fallback name
        if not self.facts.get("name"):
            self.facts["name"] = self.domain.replace("www.", "").split(".")[0].title()
        
        # Try to get description from homepage
        if not self.facts.get("description"):
            for page in self.pages:
                url = page.get("url", "")
                if any(url.rstrip('/').endswith(x) for x in [self.domain, f"www.{self.domain}"]):
                    desc = page.get("description", "")
                    if desc:
                        self.facts["description"] = desc[:200]
                    elif page.get("content"):
                        # Use first 200 chars of content
                        content = page.get("content", "")[:200]
                        if content:
                            self.facts["description"] = content + "..."
                    break
        
        # Generate default description if still empty
        if not self.facts.get("description"):
            self.facts["description"] = f"{self.facts.get('name', self.domain)} - Visit our website to learn more."
    
    def generate_all_schemas(self) -> Dict[str, str]:
        """Generate all applicable schemas"""
        schemas = {
            "organization": self.generate_organization_schema(),
            "faq": self.generate_faq_schema(),
            "software_application": self.generate_software_application_schema(),
            "howto": self.generate_howto_schema(),
        }
        return schemas
    
    def generate_organization_schema(self) -> str:
        """
        Generate Organization schema for homepage.
        Usage: Paste into <head> section of homepage.
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": self.facts.get("name", self.domain),
            "url": f"https://{self.domain}",
        }
        
        # Add description (always present after _ensure_basic_facts)
        if self.facts.get("description"):
            schema["description"] = self.facts["description"]
        
        # Add optional fields if present
        if self.facts.get("logo"):
            schema["logo"] = self.facts["logo"]
        
        if self.facts.get("sameAs"):
            schema["sameAs"] = self.facts["sameAs"]
        
        if self.facts.get("founder"):
            schema["founder"] = self.facts["founder"]
        
        if self.facts.get("foundingDate"):
            schema["foundingDate"] = self.facts["foundingDate"]
        
        if self.facts.get("address"):
            schema["address"] = self.facts["address"]
        
        html = f"""<!-- Organization Schema - Add to Homepage <head> -->
<script type="application/ld+json">
{json.dumps(schema, indent=2)}
</script>

<!-- 
DEPLOYMENT INSTRUCTIONS:
1. Copy this entire <script> block
2. Open your homepage HTML/template
3. Paste BEFORE the closing </head> tag
4. Deploy to production
5. Verify at https://validator.schema.org

WHY THIS MATTERS:
Organization schema is the Schema.org standard for identifying entities.
Google officially uses it for Knowledge Panels.
We don't have proof LLMs use it, but it's documented best practice.

Docs: https://schema.org/Organization
-->"""
        
        return html
    
    def generate_faq_schema(self) -> str:
        """
        Generate FAQ schema with extracted or template questions.
        """
        product_name = self.facts.get("name", self.domain)
        
        # Try to extract FAQs from content, or use templates
        questions = self._extract_or_generate_faqs(product_name)
        
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": q["answer"]
                    }
                }
                for q in questions
            ]
        }
        
        html = f"""<!-- FAQ Schema - Add to FAQ/Help page <head> -->
<script type="application/ld+json">
{json.dumps(schema, indent=2)}
</script>

<!-- 
DEPLOYMENT INSTRUCTIONS:
1. CUSTOMIZE the answers with your actual content (placeholders marked with [...])
2. Copy this entire <script> block
3. Paste into your FAQ/Help page <head>
4. Deploy to production
5. Verify at https://validator.schema.org

WHY THIS MATTERS:
FAQPage schema is used by Google for FAQ rich snippets.
Whether ChatGPT/Claude use it is unproven, but it structures your content well.

Docs: https://schema.org/FAQPage

BEST PRACTICE:
- Add 5-10 real FAQs from customer support
- Keep answers concise (50-200 words)
- Update quarterly with new common questions
-->"""
        
        return html
    
    def generate_software_application_schema(self) -> str:
        """
        Generate SoftwareApplication schema for product pages.
        Used by Google for rich results. LLM usage unproven.
        """
        offers = self.facts.get("makesOffer", [])
        
        # Find lowest price
        prices = [o.get("price") for o in offers if o.get("price") and str(o.get("price")).isdigit()]
        lowest_price = min(prices) if prices else 0
        
        schema = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": self.facts.get("name", self.domain),
            "description": self.facts.get("description", f"Software by {self.domain}"),
            "applicationCategory": "BusinessApplication",
            "operatingSystem": "Web-based",
            "offers": {
                "@type": "Offer",
                "price": str(lowest_price),
                "priceCurrency": "USD"
            }
        }
        
        # Add rating placeholder
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": "4.5",
            "reviewCount": "100",
            "bestRating": "5",
            "worstRating": "1"
        }
        
        html = f"""<!-- SoftwareApplication Schema - Add to Product page <head> -->
<script type="application/ld+json">
{json.dumps(schema, indent=2)}
</script>

<!-- 
DEPLOYMENT INSTRUCTIONS:
1. UPDATE aggregateRating with your real G2/Capterra/Trustpilot data
2. VERIFY price and currency are correct
3. Copy this entire <script> block
4. Paste into your main product page <head>
5. Deploy to production

WHY THIS MATTERS:
SoftwareApplication schema enables Google rich results.
Whether it helps LLM citations is unproven.

Docs: https://schema.org/SoftwareApplication

CRITICAL: The aggregateRating MUST be real data from a review platform.
Fake ratings will get you penalized.
-->"""
        
        return html
    
    def generate_howto_schema(self) -> str:
        """
        Generate HowTo schema template for guide pages.
        """
        product_name = self.facts.get("name", self.domain)
        
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": f"How to get started with {product_name}",
            "description": f"Step-by-step guide to using {product_name}",
            "step": [
                {
                    "@type": "HowToStep",
                    "name": "Step 1: Create an account",
                    "text": "[Customize: Explain your signup process]"
                },
                {
                    "@type": "HowToStep", 
                    "name": "Step 2: Configure your settings",
                    "text": "[Customize: Explain initial setup]"
                },
                {
                    "@type": "HowToStep",
                    "name": "Step 3: Start using key features",
                    "text": "[Customize: Explain core functionality]"
                }
            ]
        }
        
        html = f"""<!-- HowTo Schema - Add to Guide/Tutorial pages <head> -->
<script type="application/ld+json">
{json.dumps(schema, indent=2)}
</script>

<!-- 
DEPLOYMENT INSTRUCTIONS:
1. Fill in the step names and descriptions with your actual process
2. Add more steps as needed (3-10 steps recommended)
3. Copy this entire <script> block
4. Paste into your guide page <head>
5. Deploy to production

WHY THIS MATTERS:
HowTo schema is used by Google for step-by-step rich snippets.
Whether LLMs prioritize structured steps is unproven.

Docs: https://schema.org/HowTo

USE THIS ON:
- Getting started guides
- Tutorial pages  
- Setup documentation
- Onboarding flows
-->"""
        
        return html
    
    def _extract_or_generate_faqs(self, product_name: str) -> List[Dict]:
        """Extract Q&A pairs from pages or generate templates"""
        
        # Look for FAQ page
        faq_page = None
        for page in self.pages:
            url = page.get("url", "")
            if any(kw in url.lower() for kw in ["faq", "help", "support", "questions"]):
                faq_page = page
                break
        
        # TODO: In future, use Gemini to extract actual FAQs from page content
        
        # For now, provide smart templates based on facts
        templates = [
            {
                "question": f"What is {product_name}?",
                "answer": self.facts.get("description", f"[Customize: Add your product description]")
            },
            {
                "question": f"How much does {product_name} cost?",
                "answer": self._generate_pricing_answer()
            },
            {
                "question": f"Is there a free trial for {product_name}?",
                "answer": "[Customize: Yes, we offer a 14-day free trial / No, but we have a free tier]"
            },
            {
                "question": f"How do I get started with {product_name}?",
                "answer": "[Customize: Sign up at our website and follow the onboarding guide]"
            },
            {
                "question": f"What integrations does {product_name} support?",
                "answer": "[Customize: List your key integrations like Slack, Zapier, etc.]"
            }
        ]
        
        return templates
    
    def _generate_pricing_answer(self) -> str:
        """Generate pricing answer from facts"""
        offers = self.facts.get("makesOffer", [])
        
        if not offers:
            return "[Customize: Visit our pricing page for current plans and pricing]"
        
        pricing_parts = []
        for offer in offers[:3]:  # Top 3 plans
            name = offer.get("name", "Plan")
            price = offer.get("price", "Contact us")
            currency = offer.get("priceCurrency", "USD")
            
            if price and str(price) != "null":
                pricing_parts.append(f"{name}: ${price}/{currency}")
            else:
                pricing_parts.append(f"{name}: Contact sales")
        
        if pricing_parts:
            return f"Our plans include: {', '.join(pricing_parts)}. Visit our pricing page for full details."
        
        return "[Customize: Visit our pricing page for current plans and pricing]"


def generate_robots_txt(domain: str) -> str:
    """
    Generate optimized robots.txt for AI crawler access.
    
    This is CRITICAL - without proper robots.txt, AI crawlers are blocked.
    """
    return f"""# Robots.txt for {domain}
# Generated by CitationVault - Optimized for AI crawler access

# Allow all crawlers by default
User-agent: *
Allow: /

# Explicitly allow AI crawlers (CRITICAL for citations)
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Anthropic-AI
Allow: /

User-agent: cohere-ai
Allow: /

# Block admin/private areas (customize as needed)
Disallow: /admin/
Disallow: /api/internal/
Disallow: /private/

# Point to key files for LLMs
# (These are informal headers - LLMs may check them)
# LLM-Txt: https://{domain}/llm.txt
# Facts: https://{domain}/facts.jsonld

# Standard sitemap
Sitemap: https://{domain}/sitemap.xml
"""


def generate_llm_robots_section() -> str:
    """
    Generate the LLM-specific section to append to existing robots.txt
    """
    return """
# === CITATIONVAULT AI CRAWLER PERMISSIONS ===
# Add this section to your existing robots.txt

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Anthropic-AI
Allow: /

User-agent: cohere-ai
Allow: /

# === END CITATIONVAULT SECTION ===
"""
