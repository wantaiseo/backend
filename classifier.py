"""
CiteKit – Page Classifier
LLM-powered page classification using Gemini
Per FR-3: Semantic Classification

COST OPTIMIZED: Uses batch classification to reduce API calls
"""

import json
import logging
from typing import Optional

import google.generativeai as genai

from config import get_settings
from models import PageClassification, PageData

# Configure logging
logger = logging.getLogger("geo-compiler.classifier")


class PageClassifier:
    """
    LLM-powered page classifier using Gemini.
    Uses batch classification to minimize API costs.
    """

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.temperature = settings.llm_temperature
        self.batch_size = settings.classification_batch_size
        self.max_content_tokens = settings.max_content_tokens

    # ============================================
    # BATCH CLASSIFICATION PROMPT (cost-optimized)
    # ============================================

    BATCH_SYSTEM_PROMPT = """You are a strict page classifier.
Output valid JSON array only. No markdown, no code blocks.
Classify each page independently based on provided content."""

    BATCH_USER_TEMPLATE = """Classify these {count} webpages. Return a JSON array with exactly {count} objects.

PAGES:
{pages_data}

For EACH page, return:
{{
  "url": "the page URL",
  "page_type": "homepage|pricing|docs|blog|about|contact|legal|product|feature|api|changelog|careers|support|faq|other",
  "primary_intent": "informational|commercial|instructional|navigational|transactional",
  "topics": ["keyword1", "keyword2"],
  "confidence": 0.0-1.0
}}

Return ONLY a JSON array like: [{{"url":"...","page_type":"...","primary_intent":"...","topics":[...],"confidence":0.9}}, ...]"""

    # ============================================
    # SINGLE PAGE PROMPT (fallback)
    # ============================================

    SINGLE_SYSTEM_PROMPT = """You are a strict classifier.
Output valid JSON only. No markdown or code blocks."""

    SINGLE_USER_TEMPLATE = """Classify this webpage:

URL: {url}
Title: {title}
Description: {description}
Headings: {headings}
Content: {content}

Return exactly:
{{"page_type":"string","primary_intent":"string","topics":["string"],"confidence":0.0-1.0}}

page_type: homepage|pricing|docs|blog|about|contact|legal|product|feature|api|changelog|careers|support|faq|other
primary_intent: informational|commercial|instructional|navigational|transactional"""

    # ============================================
    # BATCH CLASSIFY (PRIMARY - cost efficient)
    # ============================================

    async def classify_batch(self, pages: list[PageData]) -> list[PageClassification]:
        """
        Classify multiple pages in a single API call.
        Reduces API costs by ~80% compared to individual calls.
        """
        if not pages:
            return []

        # Build compact page data
        pages_data = []
        for i, page in enumerate(pages):
            # Truncate content aggressively for batching
            content = (page.content or "")[:self.max_content_tokens // len(pages)]
            headings = ", ".join((page.headings or [])[:5])
            
            pages_data.append(
                f"[{i+1}] URL: {page.url}\n"
                f"Title: {page.title or 'N/A'}\n"
                f"Desc: {(page.description or '')[:100]}\n"
                f"H: {headings}\n"
                f"Content: {content[:200]}..."
            )

        prompt = self.BATCH_USER_TEMPLATE.format(
            count=len(pages),
            pages_data="\n\n".join(pages_data)
        )

        try:
            response = self.model.generate_content(
                [self.BATCH_SYSTEM_PROMPT, prompt],
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=150 * len(pages)  # ~150 tokens per page
                )
            )

            text = response.text.strip()
            
            # Clean markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            results = json.loads(text)
            
            # Map results back to pages by URL
            url_to_result = {r.get("url", ""): r for r in results}
            
            classifications = []
            for page in pages:
                result = url_to_result.get(page.url, {})
                classifications.append(PageClassification(
                    page_type=result.get("page_type", "other"),
                    primary_intent=result.get("primary_intent", "informational"),
                    topics=result.get("topics", [])[:5],
                    confidence=float(result.get("confidence", 0.5))
                ))
            
            return classifications

        except Exception as e:
            print(f"Batch classification failed: {e}, falling back to individual")
            # Fallback to individual classification
            return [await self.classify_single(p) for p in pages]

    # ============================================
    # SINGLE PAGE CLASSIFY (fallback)
    # ============================================

    async def classify_single(self, page: PageData) -> PageClassification:
        """
        Classify a single page. Used as fallback when batch fails.
        """
        content = (page.content or "")[:self.max_content_tokens]
        headings = ", ".join((page.headings or [])[:10])

        prompt = self.SINGLE_USER_TEMPLATE.format(
            url=page.url,
            title=page.title or "N/A",
            description=(page.description or "")[:150],
            headings=headings,
            content=content[:500]
        )

        try:
            response = self.model.generate_content(
                [self.SINGLE_SYSTEM_PROMPT, prompt],
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=200
                )
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)

            return PageClassification(
                page_type=data.get("page_type", "other"),
                primary_intent=data.get("primary_intent", "informational"),
                topics=data.get("topics", [])[:5],
                confidence=float(data.get("confidence", 0.5))
            )

        except Exception:
            return PageClassification(
                page_type="other",
                primary_intent="informational",
                topics=[],
                confidence=0.3
            )

    # ============================================
    # MAIN ENTRY POINT
    # ============================================

    async def classify_pages(self, pages: list[PageData]) -> list[PageData]:
        """
        Classify all pages using batched API calls.
        Updates each page's classification field.
        """
        classified = []
        
        # Process in batches
        for i in range(0, len(pages), self.batch_size):
            batch = pages[i:i + self.batch_size]
            print(f"Classifying batch {i//self.batch_size + 1} ({len(batch)} pages)...")
            
            classifications = await self.classify_batch(batch)
            
            for page, classification in zip(batch, classifications):
                page.classification = classification.model_dump()
                classified.append(page)

        return classified

    # Legacy method for backward compatibility
    async def classify_page(self, page: PageData) -> PageClassification:
        """Single page classification (legacy interface)."""
        return await self.classify_single(page)
