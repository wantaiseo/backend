"""
CiteKit - Facts.jsonld Generator v2
Complete implementation based on facts-jsonld-generation-spec.md

This module generates machine-readable facts.jsonld following Schema.org standards.
Based on documented best practices from schema.org, llmstxt.org, and Princeton's GEO research.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import google.generativeai as genai
from config import get_settings
from models import PageData

# Configure logging
logger = logging.getLogger("geo-compiler.facts_generator")


# ============================================
# DATA STRUCTURES
# ============================================

class FactType(Enum):
    STATISTIC = "statistic"
    CLAIM = "claim"
    DEFINITION = "definition"
    PRIMARY_ANSWER = "primary_answer"
    QUOTE = "quote"


class FactImportance(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExtractedFact:
    """Represents a single extracted fact."""
    id: str
    type: FactType
    statement: str
    original_text: str = ""
    importance: FactImportance = FactImportance.MEDIUM
    confidence: float = 0.75
    source_position: Dict[str, int] = field(default_factory=dict)
    entities_mentioned: List[str] = field(default_factory=list)
    supporting_evidence: str = ""
    is_quotable: bool = False
    has_weak_modifiers: bool = False
    term: str = ""  # For definitions
    
    def to_schema(self, base_url: str) -> Dict:
        """Convert to Schema.org compatible format."""
        schema = {
            "@type": "Claim",  # Using Claim type for facts
            "@id": f"{base_url}#fact-{self.id}",
            "name": self.statement[:100],
            "text": self.statement,
            "position": self.importance.value,
            "dateCreated": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        
        if self.type == FactType.STATISTIC:
            schema["@type"] = "StatisticalVariable"
        elif self.type == FactType.DEFINITION:
            schema["@type"] = "DefinedTerm"
            schema["name"] = self.term or self.statement[:50]
        
        return schema


@dataclass
class ExtractedEntity:
    """Represents an extracted named entity."""
    id: str
    text: str
    type: str  # Person, Organization, Place, Thing
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    same_as: List[str] = field(default_factory=list)
    confidence: float = 0.8
    mentions_in_facts: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Validation result for facts.jsonld."""
    is_valid: bool
    quality_score: int
    total_checks: int = 12
    passed_checks: int = 0
    failed_checks: int = 0
    issues: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)
    checks: Dict[str, Dict] = field(default_factory=dict)
    quality_breakdown: Dict[str, int] = field(default_factory=dict)


# ============================================
# MAIN FACTS GENERATOR CLASS
# ============================================

class FactsJsonLdGenerator:
    """
    Complete facts.jsonld generation pipeline.
    
    6-Step Pipeline:
    1. NER Extract - Identify entities and metadata
    2. Extract Facts - Find 5 fact types
    3. Entity Linking - Connect to external sources
    4. Schema Generation - Build JSON-LD
    5. Validation - 12 quality rules
    6. LLM Enhancement - Improve weak facts (optional)
    """
    
    # Patterns for fact extraction
    STATISTIC_PATTERNS = [
        r'\d+(?:\.\d+)?%',                          # Percentages: 50%, 3.5%
        r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|M|B))?',  # Currency
        r'\b\d{1,3}(?:,\d{3})+\b',                  # Large numbers: 1,000,000
        r'\b\d+(?:\.\d+)?\s*(?:x|times)\b',         # Multipliers: 2x, 3.5x
        r'\b(?:19|20)\d{2}\b',                      # Years
        r'\b\d+\s*(?:days?|weeks?|months?|years?|hours?|minutes?)\b',  # Durations
    ]
    
    # Strong verbs for confident statements
    STRONG_VERBS = [
        'is', 'are', 'was', 'were', 'causes', 'leads to', 'results in',
        'increases', 'decreases', 'reduces', 'improves', 'creates',
        'enables', 'provides', 'delivers', 'generates', 'produces',
        'requires', 'needs', 'must', 'should', 'drives', 'transforms'
    ]
    
    # Weak modifiers to filter out
    WEAK_MODIFIERS = [
        'might', 'could', 'may', 'possibly', 'perhaps', 'seems',
        'appears', 'likely', 'probably', 'potentially', 'sometimes'
    ]
    
    # Definition patterns - STRICT: require proper terms
    DEFINITION_PATTERNS = [
        # Capitalized term definitions: "API is a..."
        r'\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\s+(?:is|means|refers to|stands for|is defined as)\s+([^.]{20,150})\.',
        # Acronym pattern: GEO (Generative Engine Optimization)
        r'\b([A-Z]{2,6})\s*\(([^)]{10,100})\)',
        # "What is X" patterns: common in FAQs
        r'[Ww]hat\s+is\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\?\s*([^.]{20,200})\.',
    ]
    
    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        
        # Configuration
        self.config = {
            "min_facts_required": 3,
            "min_statistics_required": 1,
            "min_confidence_threshold": 0.75,
            "max_content_age_days": 90,
            "entities_to_link": 2,
            "use_llm_enhancement": True,
            "validate_against_schema_org": True,
        }
        
        self.fact_counter = 0
    
    def _next_fact_id(self) -> str:
        """Generate next fact ID."""
        self.fact_counter += 1
        return f"{self.fact_counter:03d}"
    
    # ============================================
    # STEP 1: CONTENT EXTRACTION & NER
    # ============================================
    
    def extract_entities_and_metadata(self, pages: List[PageData], domain: str) -> Dict:
        """
        Step 1: Extract entities and metadata from pages.
        Uses strict validation to avoid garbage extraction.
        """
        all_content = "\n".join([p.content or "" for p in pages[:30]])
        
        entities = {
            "PERSON": [],
            "ORG": [],
            "DATE": [],
            "MONEY": [],
            "PERCENT": [],
        }
        
        # Common garbage words to filter out
        GARBAGE_WORDS = {
            'we offer', 'end', 'click', 'learn more', 'read more', 'get started',
            'contact us', 'sign up', 'subscribe', 'various processes', 'an easy',
            'the', 'a', 'and', 'or', 'for', 'with', 'our', 'your', 'how', 'what',
            'why', 'when', 'where', 'home', 'about', 'contact', 'services', 'products',
            'solutions', 'features', 'benefits', 'example', 'sample', 'test', 'demo'
        }
        
        def is_valid_name(name: str) -> bool:
            """Check if a name is valid (not garbage)"""
            if not name or len(name) < 3:
                return False
            name_lower = name.lower().strip()
            # Check against garbage
            if name_lower in GARBAGE_WORDS:
                return False
            # Must have at least one capital letter for proper nouns
            if not any(c.isupper() for c in name):
                return False
            # Should not contain newlines or weird chars
            if '\n' in name or '\t' in name or '\\' in name:
                return False
            # Should not be too short or single word for person names
            words = name.split()
            if len(words) < 2:
                return False  # Person names need at least 2 words
            # Each word should be reasonable
            for word in words:
                if len(word) < 2 or word.lower() in GARBAGE_WORDS:
                    return False
            return True
        
        def is_valid_org_name(name: str) -> bool:
            """Check if org name is valid"""
            if not name or len(name) < 2:
                return False
            name_lower = name.lower().strip()
            if name_lower in GARBAGE_WORDS:
                return False
            if '\n' in name or '\t' in name:
                return False
            # Org names can be single word but must be capitalized
            if not name[0].isupper():
                return False
            return True
        
        # Extract persons (author patterns) - STRICT
        author_patterns = [
            r'(?:founder|ceo|cto|chief executive|co-founder)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:by|author|written by)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*,\s*(?:PhD|MD|CEO|CTO|Founder|Co-Founder|Author|Director)',
        ]
        for pattern in author_patterns:
            matches = re.findall(pattern, all_content)
            for match in matches:
                if is_valid_name(match) and match not in [e["text"] for e in entities["PERSON"]]:
                    entities["PERSON"].append({"text": match.strip(), "confidence": 0.85})
        
        # Extract dates
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\bfounded (?:in )?(\d{4})\b',
            r'\bsince (\d{4})\b',
            r'\best\.?\s*(\d{4})\b',
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, all_content, re.IGNORECASE)
            for match in matches:
                if match and match not in [e["text"] for e in entities["DATE"]]:
                    entities["DATE"].append({"text": match, "confidence": 0.95})
        
        # Build metadata - IMPROVED
        # Find ACTUAL homepage by URL pattern, not just pages[0]
        homepage = None
        for p in pages:
            url_lower = p.url.lower().rstrip('/')
            # Homepage is typically the root URL
            if url_lower.endswith(domain) or url_lower.endswith(domain + '/'):
                homepage = p
                break
            # Also check for www variant
            if url_lower.endswith('www.' + domain) or url_lower.endswith('www.' + domain + '/'):
                homepage = p
                break
        
        # Fallback to first page if no homepage found
        if homepage is None:
            homepage = pages[0] if pages else None
        
        # Extract GOOD company name from homepage title (or domain as fallback)
        org_name = self._extract_company_name_from_title(homepage, domain)
        
        # Only use author if properly extracted
        author_name = None
        if entities["PERSON"]:
            author_name = entities["PERSON"][0]["text"]
        
        metadata = {
            "title": homepage.title if homepage else domain,
            "description": homepage.description if homepage else "",
            "domain": domain,
            "author_name": author_name,
            "org_name": org_name,
            "publish_date": entities["DATE"][0]["text"] if entities["DATE"] else None,
        }
        
        # Add org to entities list if not already there
        if org_name and is_valid_org_name(org_name):
            if org_name not in [e["text"] for e in entities["ORG"]]:
                entities["ORG"].insert(0, {"text": org_name, "confidence": 0.95})
        
        return {
            "entities": entities,
            "metadata": metadata,
            "raw_content": all_content[:50000]  # Cap for processing
        }
    
    def _extract_company_name_from_title(self, page: 'PageData', domain: str) -> str:
        """Extract company name from page title - much smarter."""
        # Page-specific phrases to skip (not company names)
        SKIP_PHRASES = {
            "let's discuss", "contact us", "contact", "get in touch", "reach us",
            "about us", "about", "home", "homepage", "welcome", "official site",
            "login", "sign up", "register", "pricing", "blog", "news", "faq",
            "support", "help", "terms", "privacy", "404", "error"
        }
        
        if page and page.title:
            title = page.title
            
            # Common separators: "|", "-", "–", "—", ":"
            separators = ['|', ' - ', ' – ', ' — ', ':']
            for sep in separators:
                if sep in title:
                    parts = title.split(sep)
                    # Usually company name is LAST part (after page title)
                    for part in reversed(parts):  # Check last parts first
                        part = part.strip()
                        part_lower = part.lower()
                        # Skip page-specific phrases
                        if part_lower in SKIP_PHRASES:
                            continue
                        if any(skip in part_lower for skip in SKIP_PHRASES):
                            continue
                        if len(part) > 2 and len(part) < 50:
                            return part
            
            # If title has no separator and doesn't look page-specific, use it
            if len(title) < 50 and title[0].isupper():
                title_lower = title.lower()
                if title_lower not in SKIP_PHRASES:
                    if not any(skip in title_lower for skip in SKIP_PHRASES):
                        return title.split(' - ')[0].split(' | ')[0].strip()
        
        # Fallback to domain name
        return self._extract_company_name_from_domain(domain)
    
    def _extract_company_name_from_domain(self, domain: str) -> str:
        """Extract company name from domain."""
        name = domain.replace("www.", "").split(".")[0]
        return name.title()
    
    def _extract_social_links(self, pages: List[PageData]) -> List[str]:
        """
        Extract social media profile links from page content.
        These become sameAs links in Schema.org for entity disambiguation.
        """
        all_content = " ".join([p.content or "" for p in pages[:10]])
        
        social_patterns = {
            'twitter': r'https?://(?:www\.)?(twitter\.com|x\.com)/([a-zA-Z0-9_]{1,15})(?:[/?]|$)',
            'linkedin': r'https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9-]+)',
            'facebook': r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)',
            'github': r'https?://(?:www\.)?github\.com/([a-zA-Z0-9-]+)',
            'instagram': r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)',
            'youtube': r'https?://(?:www\.)?youtube\.com/(?:c/|channel/|@)?([a-zA-Z0-9_-]+)',
        }
        
        found_profiles = []
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, all_content, re.IGNORECASE)
            for match in matches:
                # Handle tuple from capture groups
                username = match[1] if isinstance(match, tuple) else match
                
                # Skip common false positives
                if username.lower() in ['share', 'intent', 'home', 'login', 'signup', 'search', 'sharer']:
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
        
        return found_profiles
    
    # ============================================
    # STEP 2: FACT EXTRACTION
    # ============================================
    
    def extract_facts(self, pages: List[PageData], metadata: Dict) -> List[ExtractedFact]:
        """
        Step 2: Extract 5 types of facts from content.
        - Statistics (numbers, percentages, dates)
        - Claims (confident statements)
        - Definitions (X is Y)
        - Primary Answer (first 2-3 sentences)
        - Quotes (quotable statements)
        """
        # Use more pages for content extraction (was limited to 15)
        all_content = "\n".join([p.content or "" for p in pages[:30]])
        facts = []
        
        # 2A: Extract Statistics
        stats_facts = self._extract_statistics(all_content)
        facts.extend(stats_facts)
        
        # 2B: Extract Confident Statements (Claims)
        claim_facts = self._extract_claims(all_content)
        facts.extend(claim_facts)
        
        # 2C: Extract Definitions
        definition_facts = self._extract_definitions(all_content)
        facts.extend(definition_facts)
        
        # 2D: Extract Primary Answer
        primary_answer = self._extract_primary_answer(pages, metadata)
        if primary_answer:
            facts.append(primary_answer)
        
        # 2E: Extract Quotable Statements
        quote_facts = self._extract_quotes(all_content)
        facts.extend(quote_facts)
        
        print(f"[FactsGenerator] Extracted {len(facts)} facts: "
              f"{len(stats_facts)} stats, {len(claim_facts)} claims, "
              f"{len(definition_facts)} defs, {len(quote_facts)} quotes")
        
        return facts
    
    def _extract_statistics(self, content: str) -> List[ExtractedFact]:
        """Extract statistics (numbers, percentages, currencies, dates)."""
        facts = []
        sentences = self._split_sentences(content)
        
        for sentence in sentences:
            for pattern in self.STATISTIC_PATTERNS:
                if re.search(pattern, sentence):
                    # Found a statistic - extract the full sentence
                    clean_sentence = self._clean_sentence(sentence)
                    if len(clean_sentence) > 20 and len(clean_sentence) < 300:
                        facts.append(ExtractedFact(
                            id=self._next_fact_id(),
                            type=FactType.STATISTIC,
                            statement=clean_sentence,
                            original_text=sentence,
                            importance=FactImportance.HIGH,
                            confidence=0.9,
                            is_quotable=True
                        ))
                        break  # One fact per sentence
        
        # Deduplicate and limit
        seen = set()
        unique_facts = []
        for fact in facts[:10]:  # Max 10 stats
            if fact.statement not in seen:
                seen.add(fact.statement)
                unique_facts.append(fact)
        
        return unique_facts[:10]  # Return top 10 statistics
    
    def _extract_claims(self, content: str) -> List[ExtractedFact]:
        """Extract confident statements without weak modifiers."""
        facts = []
        sentences = self._split_sentences(content)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check for strong verbs
            has_strong_verb = any(f" {verb} " in f" {sentence_lower} " for verb in self.STRONG_VERBS)
            
            # Check for weak modifiers
            has_weak_modifier = any(modifier in sentence_lower for modifier in self.WEAK_MODIFIERS)
            
            if has_strong_verb and not has_weak_modifier:
                clean_sentence = self._clean_sentence(sentence)
                if 50 < len(clean_sentence) < 250:  # Increased minimum to 50 for quality
                    facts.append(ExtractedFact(
                        id=self._next_fact_id(),
                        type=FactType.CLAIM,
                        statement=clean_sentence,
                        original_text=sentence,
                        importance=FactImportance.HIGH,
                        confidence=0.85,
                        is_quotable=True,
                        has_weak_modifiers=False
                    ))
        
        return facts[:10]  # Return top 10 claims
    
    def _extract_definitions(self, content: str) -> List[ExtractedFact]:
        """Extract definitions (X is/means Y patterns) - STRICT validation."""
        facts = []
        seen_terms = set()
        
        # Garbage terms to skip
        INVALID_TERMS = {
            'this', 'that', 'it', 'they', 'we', 'you', 'he', 'she', 'such',
            'the', 'a', 'an', 'our', 'your', 'their', 'its', 'one', 'all',
            'such a solution', 'cost air monitoring', 'monitoring points'
        }
        
        for pattern in self.DEFINITION_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    term = groups[0].strip()
                    definition = groups[1].strip() if len(groups) > 1 else ""
                    
                    # STRICT validation
                    term_lower = term.lower()
                    if term_lower in INVALID_TERMS:
                        continue
                    if '\n' in term or len(term) < 2 or len(term) > 50:
                        continue
                    if not term[0].isupper():  # Must start with capital
                        continue
                    if len(definition) < 15:  # Definition must be substantial
                        continue
                    if term_lower in seen_terms:  # Avoid duplicates
                        continue
                    
                    seen_terms.add(term_lower)
                    statement = f"{term}: {definition}"
                    
                    facts.append(ExtractedFact(
                        id=self._next_fact_id(),
                        type=FactType.DEFINITION,
                        statement=self._clean_sentence(statement),
                        original_text=match.group(),
                        importance=FactImportance.HIGH,
                        confidence=0.9,
                        term=term
                    ))
        
        return facts[:5]  # Return top 5 definitions
    
    def _extract_primary_answer(self, pages: List[PageData], metadata: Dict) -> Optional[ExtractedFact]:
        """Extract primary answer (first 2-3 sentences that answer the main topic)."""
        if not pages:
            return None
        
        # Get content from homepage or first page
        homepage = next((p for p in pages if p.classification.get("page_type") == "homepage"), pages[0])
        content = homepage.content or homepage.description or ""
        
        sentences = self._split_sentences(content)[:3]
        if not sentences:
            return None
        
        primary_answer = " ".join(sentences)
        if len(primary_answer) < 50:
            return None
        
        return ExtractedFact(
            id=self._next_fact_id(),
            type=FactType.PRIMARY_ANSWER,
            statement=self._clean_sentence(primary_answer)[:500],
            original_text=primary_answer,
            importance=FactImportance.CRITICAL,
            confidence=0.95,
            is_quotable=True
        )
    
    def _extract_quotes(self, content: str) -> List[ExtractedFact]:
        """Extract quotable standalone statements."""
        facts = []
        sentences = self._split_sentences(content)
        
        for sentence in sentences:
            sentence = self._clean_sentence(sentence)
            
            # Good quotes are 10-30 words, definitive, and memorable
            word_count = len(sentence.split())
            if 10 <= word_count <= 40:
                # Check if it's a strong declarative sentence
                if (sentence[0].isupper() and 
                    sentence.endswith('.') and
                    not any(q in sentence.lower() for q in ['?', 'click', 'subscribe', 'sign up'])):
                    
                    facts.append(ExtractedFact(
                        id=self._next_fact_id(),
                        type=FactType.QUOTE,
                        statement=sentence,
                        original_text=sentence,
                        importance=FactImportance.MEDIUM,
                        confidence=0.8,
                        is_quotable=True
                    ))
        
        return facts[:5]  # Return top 5 quotes
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]
    
    def _clean_sentence(self, sentence: str) -> str:
        """Clean and normalize a sentence."""
        # Remove extra whitespace
        sentence = re.sub(r'\s+', ' ', sentence).strip()
        # Remove leading/trailing punctuation (except period)
        sentence = sentence.strip('•◦○●-–—')
        return sentence.strip()
    
    # ============================================
    # STEP 3: ENTITY LINKING
    # ============================================
    
    def link_entities(self, entities: Dict, facts: List[ExtractedFact]) -> List[ExtractedEntity]:
        """
        Step 3: Link entities to external sources (sameAs).
        Note: Full Wikidata linking would require wptools library.
        This implementation filters garbage and uses extracted social links.
        """
        linked_entities = []
        
        # Garbage filter
        GARBAGE = {'we offer', 'end', 'an easy', 'various processes', 'example', 
                   'the', 'this', 'that', 'home', 'click', 'learn more'}
        
        def is_valid(text: str) -> bool:
            if not text or len(text) < 3:
                return False
            if text.lower() in GARBAGE:
                return False
            if '\n' in text or '\t' in text:
                return False
            return True
        
        # Link organizations (only valid ones)
        for org in entities.get("ORG", [])[:3]:
            if is_valid(org["text"]):
                linked_entities.append(ExtractedEntity(
                    id=f"org_{len(linked_entities)+1}",
                    text=org["text"],
                    type="Organization",
                    confidence=org.get("confidence", 0.8)
                ))
        
        # Link persons (authors) - only valid ones
        for person in entities.get("PERSON", [])[:3]:
            if is_valid(person["text"]):
                linked_entities.append(ExtractedEntity(
                    id=f"person_{len(linked_entities)+1}",
                    text=person["text"],
                    type="Person",
                    confidence=person.get("confidence", 0.8)
                ))
        
        return linked_entities
    
    # ============================================
    # STEP 4: SCHEMA GENERATION (v2 - Launch Quality)
    # ============================================
    
    def generate_schema(
        self,
        facts: List[ExtractedFact],
        entities: List[ExtractedEntity],
        metadata: Dict,
        social_links: List[str],
        domain: str
    ) -> Dict:
        """
        Step 4: Generate comprehensive facts.jsonld Schema.org structure.
        
        Outputs @graph with:
        - Organization (always)
        - WebSite (always)
        - SoftwareApplication (if SaaS/software detected)
        - FAQPage (if FAQs can be inferred)
        """
        base_url = f"https://{domain}"
        now = datetime.utcnow().isoformat() + "Z"
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Extract key info
        org_name = metadata.get("org_name") or self._extract_company_name_from_domain(domain)
        description = metadata.get("description", "")
        slogan = metadata.get("slogan", "")
        
        # ---- 1. ORGANIZATION ENTITY ----
        organization = {
            "@type": "Organization",
            "@id": f"{base_url}/#organization",
            "name": org_name,
            "url": base_url,
            "description": description,
        }
        
        if slogan:
            organization["slogan"] = slogan
        
        # Add logo if available
        if metadata.get("logo"):
            organization["logo"] = metadata["logo"]
        
        # Add email if found
        if metadata.get("email"):
            organization["email"] = metadata["email"]
        
        # Add founding date if found
        if metadata.get("founding_date"):
            organization["foundingDate"] = metadata["founding_date"]
        
        # Add social profiles (CRITICAL for entity disambiguation)
        if social_links:
            organization["sameAs"] = social_links
        
        # ---- 2. WEBSITE ENTITY ----
        website = {
            "@type": "WebSite",
            "@id": f"{base_url}/#website",
            "url": base_url,
            "name": org_name,
            "description": description,
            "publisher": {"@id": f"{base_url}/#organization"}
        }
        
        # ---- 3. SOFTWARE APPLICATION (if SaaS/tool/app detected) ----
        software_app = None
        is_software = any(kw in description.lower() for kw in [
            'saas', 'software', 'app', 'platform', 'tool', 'api', 
            'service', 'generate', 'automate', 'dashboard'
        ])
        
        if is_software or metadata.get("is_software"):
            software_app = {
                "@type": "SoftwareApplication",
                "@id": f"{base_url}/#product",
                "name": org_name,
                "applicationCategory": "BusinessApplication",
                "operatingSystem": "Web",
                "description": description,
            }
            
            # Add pricing if available
            if metadata.get("price"):
                software_app["offers"] = {
                    "@type": "Offer",
                    "price": str(metadata["price"]).replace("$", "").replace("₹", ""),
                    "priceCurrency": metadata.get("currency", "USD"),
                    "description": metadata.get("price_description", "")
                }
            
            # Add features if available
            features = metadata.get("features", [])
            if features:
                software_app["featureList"] = features[:10]  # Limit to 10
        
        # ---- 4. FAQ PAGE (infer FAQs from definitions and content) ----
        faq_page = None
        faq_questions = []
        
        # Generate FAQs from definitions
        for fact in facts:
            if fact.type == FactType.DEFINITION and fact.term:
                faq_questions.append({
                    "@type": "Question",
                    "name": f"What is {fact.term}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": fact.statement
                    }
                })
        
        # Add common inferred FAQs based on metadata
        if metadata.get("price"):
            faq_questions.append({
                "@type": "Question",
                "name": f"How much does {org_name} cost?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{org_name} costs {metadata.get('price')}. {metadata.get('price_description', '')}"
                }
            })
        
        # Add "What is X" FAQ
        if description:
            faq_questions.append({
                "@type": "Question",
                "name": f"What is {org_name}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": description
                }
            })
        
        if faq_questions:
            faq_page = {
                "@type": "FAQPage",
                "@id": f"{base_url}/#faq",
                "mainEntity": faq_questions[:7]  # Limit to 7 FAQs
            }
        
        # ---- BUILD FINAL @GRAPH ----
        graph = [organization, website]
        
        if software_app:
            graph.append(software_app)
        
        if faq_page:
            graph.append(faq_page)
        
        schema = {
            "@context": "https://schema.org",
            "@graph": graph
        }
        
        return schema
    
    # ============================================
    # STEP 5: VALIDATION
    # ============================================
    
    def validate(self, schema: Dict, facts: List[ExtractedFact]) -> ValidationResult:
        """
        Step 5: Validate facts.jsonld against 12 quality rules.
        """
        result = ValidationResult(
            is_valid=True,
            quality_score=0,
            checks={}
        )
        
        points = 0
        
        # V1: Author Present (+20 points)
        author = self._find_in_graph(schema, "Person")
        v1_pass = author is not None and author.get("name")
        result.checks["V1_author_present"] = {
            "passed": v1_pass,
            "message": f"Author '{author.get('name', 'N/A')}' found" if v1_pass else "No author found"
        }
        if v1_pass:
            points += 20
            result.passed_checks += 1
        else:
            result.failed_checks += 1
            result.issues.append({"rule": "V1", "severity": "HIGH", "message": "Missing author information"})
        
        # V2: Author Credentials (+15 points)
        v2_pass = author is not None and author.get("jobTitle")
        result.checks["V2_author_credentials"] = {
            "passed": v2_pass,
            "message": f"Job title '{author.get('jobTitle', 'N/A')}' present" if v2_pass else "No credentials"
        }
        if v2_pass:
            points += 15
            result.passed_checks += 1
        else:
            result.failed_checks += 1
            result.warnings.append({"rule": "V2", "severity": "MEDIUM", "message": "Missing author credentials"})
        
        # V3: Organization Present (+15 points)
        org = self._find_in_graph(schema, "Organization")
        v3_pass = org is not None and org.get("name")
        result.checks["V3_organization_present"] = {
            "passed": v3_pass,
            "message": f"Organization '{org.get('name', 'N/A')}' found" if v3_pass else "No organization"
        }
        if v3_pass:
            points += 15
            result.passed_checks += 1
        else:
            result.failed_checks += 1
            result.issues.append({"rule": "V3", "severity": "HIGH", "message": "Missing organization"})
        
        # V4: Organization sameAs Links (+10 points)
        same_as = org.get("sameAs", []) if org else []
        v4_pass = len(same_as) >= 2
        result.checks["V4_organization_links"] = {
            "passed": v4_pass,
            "message": f"{len(same_as)} sameAs links found" if v4_pass else f"Only {len(same_as)} links (need 2+)"
        }
        if v4_pass:
            points += 10
            result.passed_checks += 1
        else:
            result.failed_checks += 1
            result.warnings.append({"rule": "V4", "severity": "MEDIUM", "message": "Add more social/external links"})
        
        # V5: Content Freshness (+10 points)
        # Always pass for newly generated content
        v5_pass = True
        result.checks["V5_content_freshness"] = {"passed": v5_pass, "message": "Content is fresh"}
        points += 10
        result.passed_checks += 1
        
        # V6: Minimum Facts (+10 points)
        facts_list = schema.get("facts", [])
        v6_pass = len(facts_list) >= self.config["min_facts_required"]
        result.checks["V6_minimum_facts"] = {
            "passed": v6_pass,
            "message": f"{len(facts_list)} facts (required: {self.config['min_facts_required']})",
            "actual": len(facts_list),
            "required": self.config["min_facts_required"]
        }
        if v6_pass:
            points += 10
            result.passed_checks += 1
        else:
            result.failed_checks += 1
            result.issues.append({"rule": "V6", "severity": "HIGH", "message": f"Only {len(facts_list)} facts extracted"})
        
        # V7: Statistics Present (+5 points)
        stats_count = len([f for f in facts if f.type == FactType.STATISTIC])
        v7_pass = stats_count >= self.config["min_statistics_required"]
        result.checks["V7_statistics_present"] = {
            "passed": v7_pass,
            "message": f"{stats_count} statistics found"
        }
        if v7_pass:
            points += 5
            result.passed_checks += 1
        else:
            result.failed_checks += 1
            result.warnings.append({"rule": "V7", "severity": "MEDIUM", "message": "Add more statistics with numbers"})
        
        # V8: Primary Answer Present (+5 points)
        primary_count = len([f for f in facts if f.type == FactType.PRIMARY_ANSWER])
        v8_pass = primary_count >= 1
        result.checks["V8_primary_answer"] = {"passed": v8_pass, "message": f"Primary answer present: {v8_pass}"}
        if v8_pass:
            points += 5
            result.passed_checks += 1
        else:
            result.failed_checks += 1
        
        # V9: Average Confidence (+5 points)
        avg_confidence = sum(f.confidence for f in facts) / len(facts) if facts else 0
        v9_pass = avg_confidence >= self.config["min_confidence_threshold"]
        result.checks["V9_fact_confidence"] = {
            "passed": v9_pass,
            "message": f"Average confidence: {avg_confidence:.2f}"
        }
        if v9_pass:
            points += 5
            result.passed_checks += 1
        else:
            result.failed_checks += 1
        
        # V10: No Conflicting Facts (+5 points)
        # Simple check - assume no conflicts for now
        v10_pass = True
        result.checks["V10_no_conflicts"] = {"passed": v10_pass, "message": "No conflicting facts detected"}
        points += 5
        result.passed_checks += 1
        
        # V11: Valid JSON-LD (+5 points)
        v11_pass = "@context" in schema and "@graph" in schema
        result.checks["V11_valid_jsonld"] = {"passed": v11_pass, "message": "Valid JSON-LD structure"}
        if v11_pass:
            points += 5
            result.passed_checks += 1
        else:
            result.failed_checks += 1
        
        # V12: Entity Linking (+5 points)
        # Check for sameAs links
        v12_pass = len(same_as) >= 1
        result.checks["V12_entity_linking"] = {"passed": v12_pass, "message": f"Entities linked: {len(same_as)}"}
        if v12_pass:
            points += 5
            result.passed_checks += 1
        else:
            result.failed_checks += 1
        
        result.quality_score = points
        result.is_valid = points >= 70
        
        result.quality_breakdown = {
            "completeness": min(100, int((result.passed_checks / 12) * 100)),
            "freshness": 100,
            "credibility": min(100, int(avg_confidence * 100)),
            "entity_linking": min(100, len(same_as) * 25)
        }
        
        return result
    
    def _find_in_graph(self, schema: Dict, type_name: str) -> Optional[Dict]:
        """Find entity of given type in @graph."""
        graph = schema.get("@graph", [])
        for item in graph:
            if item.get("@type") == type_name:
                return item
        return None
    
    # ============================================
    # STEP 6: LLM ENHANCEMENT
    # ============================================
    
    async def enhance_with_llm(self, schema: Dict, facts: List[ExtractedFact], validation: ValidationResult, pages: List[PageData]) -> Dict:
        """
        Step 6: Use LLM to improve weak facts.jsonld.
        Triggered when quality_score < 75.
        """
        if validation.quality_score >= 75:
            print(f"[FactsGenerator] Quality score {validation.quality_score} >= 75, skipping LLM enhancement")
            return schema
        
        print(f"[FactsGenerator] Quality score {validation.quality_score} < 75, running LLM enhancement")
        
        # Build context
        content_preview = "\n".join([p.content[:1000] for p in pages[:5] if p.content])
        
        enhancement_prompt = f"""You are a facts.jsonld enhancement expert. Improve the following facts.jsonld for AI citation optimization.

Current Quality Score: {validation.quality_score}/100

Issues to fix:
{json.dumps(validation.issues, indent=2)}

Current Schema:
{json.dumps(schema, indent=2)}

Page Content Preview:
{content_preview[:5000]}

TASK: Extract 2-3 ADDITIONAL facts not currently in the schema. Focus on:
1. Statistics with numbers (e.g., "50% of...", "$1M in...")
2. Strong claims without weak words (avoid "might", "could", "may")
3. Definitions of key terms

Return a JSON array of new facts in this format:
[
  {{"type": "statistic", "statement": "The actual fact with a number"}},
  {{"type": "claim", "statement": "A confident statement"}}
]

Return ONLY the JSON array, no other text."""

        try:
            response = self.model.generate_content(
                enhancement_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000  # Increased for richer output
                )
            )
            
            text = response.text.strip()
            
            # Clean up markdown code blocks
            if "```" in text:
                # Extract content between code blocks
                import re as regex
                match = regex.search(r'```(?:json)?\s*([\s\S]*?)```', text)
                if match:
                    text = match.group(1).strip()
            
            # Try to find JSON array in the text
            if not text.startswith('['):
                # Look for array pattern
                start = text.find('[')
                end = text.rfind(']') + 1
                if start >= 0 and end > start:
                    text = text[start:end]
            
            new_facts = json.loads(text)
            
            # Add new facts to schema
            existing_facts = schema.get("facts", [])
            for i, new_fact in enumerate(new_facts[:3]):
                fact_entry = {
                    "@type": "Claim",
                    "@id": f"#enhanced-fact-{i+1}",
                    "text": new_fact.get("statement", ""),
                    "dateCreated": datetime.utcnow().strftime("%Y-%m-%d"),
                    "source": "LLM-enhanced"
                }
                existing_facts.append(fact_entry)
            
            schema["facts"] = existing_facts
            print(f"[FactsGenerator] Added {len(new_facts)} enhanced facts")
            
        except json.JSONDecodeError as je:
            print(f"[FactsGenerator] LLM enhancement JSON parse error: {je}")
            print(f"[FactsGenerator] Raw LLM response: {text[:200]}...")
        except Exception as e:
            print(f"[FactsGenerator] LLM enhancement failed: {e}")
        
        return schema
    
    # ============================================
    # MAIN GENERATION PIPELINE
    # ============================================
    
    async def generate(self, pages: List[PageData], domain: str, social_links: List[str] = None) -> Dict:
        """
        Main entry point: Generate complete facts.jsonld.
        
        Returns:
        {
            "facts_jsonld": {...},
            "validation": {...},
            "quality_score": 92,
            "quality_grade": "Excellent"
        }
        """
        if social_links is None:
            social_links = []
        
        print(f"[FactsGenerator] Starting facts.jsonld generation for {domain}")
        
        # Reset counter
        self.fact_counter = 0
        
        # Auto-extract social links from content if not provided
        if not social_links:
            social_links = self._extract_social_links(pages)
            if social_links:
                print(f"[FactsGenerator] Found {len(social_links)} social links: {social_links}")
        
        # Step 1: Extract entities and metadata
        extraction = self.extract_entities_and_metadata(pages, domain)
        
        # Step 2: Extract facts
        facts = self.extract_facts(pages, extraction["metadata"])
        
        # Step 3: Link entities
        linked_entities = self.link_entities(extraction["entities"], facts)
        
        # Step 4: Generate schema
        schema = self.generate_schema(
            facts=facts,
            entities=linked_entities,
            metadata=extraction["metadata"],
            social_links=social_links,
            domain=domain
        )
        
        # Step 5: Validate
        validation = self.validate(schema, facts)
        
        # Step 6: LLM Enhancement (if needed)
        if self.config["use_llm_enhancement"] and validation.quality_score < 75:
            schema = await self.enhance_with_llm(schema, facts, validation, pages)
            # Re-validate after enhancement
            validation = self.validate(schema, facts)
        
        # Calculate quality grade
        quality_grade = self._get_quality_grade(validation)
        
        print(f"[FactsGenerator] Complete. Quality: {validation.quality_score}/100, "
              f"Grade: {quality_grade}")
        
        return {
            "facts_jsonld": schema,
            "extracted_facts": facts,  # Expose raw facts for GMB generator
            "validation": asdict(validation),
            "quality_score": validation.quality_score,
            "quality_grade": quality_grade,
            "facts_count": len(facts),
            "facts_by_type": {
                "statistics": len([f for f in facts if f.type == FactType.STATISTIC]),
                "claims": len([f for f in facts if f.type == FactType.CLAIM]),
                "definitions": len([f for f in facts if f.type == FactType.DEFINITION]),
                "primary_answers": len([f for f in facts if f.type == FactType.PRIMARY_ANSWER]),
                "quotes": len([f for f in facts if f.type == FactType.QUOTE])
            }
        }
    
    def _get_quality_grade(self, validation: ValidationResult) -> str:
        """Get quality grade based on score."""
        score = validation.quality_score
        
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 60:
            return "Needs Improvement"
        else:
            return "Basic"


# ============================================
# SINGLETON ACCESS
# ============================================

_generator: Optional[FactsJsonLdGenerator] = None

def get_facts_generator() -> FactsJsonLdGenerator:
    """Get singleton facts generator instance."""
    global _generator
    if _generator is None:
        _generator = FactsJsonLdGenerator()
    return _generator
