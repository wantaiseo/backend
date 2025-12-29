# facts.jsonld Generation - Complete Technical Specification

## Document Purpose
This document provides a complete technical specification for implementing the `facts.jsonld` generation pipeline in your tool. It includes:
- End-to-end algorithm breakdown
- Data structures and interfaces
- Code examples in Python
- Validation rules
- Output specifications
- Integration points

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pipeline Steps](#pipeline-steps)
4. [Data Structures](#data-structures)
5. [Implementation Details](#implementation-details)
6. [Validation Rules](#validation-rules)
7. [API Specification](#api-specification)
8. [Examples](#examples)

---

## Overview

### What is facts.jsonld?
A machine-readable JSON-LD document that extracts and structures valuable facts from web pages. AI systems (ChatGPT, Claude, Gemini, Perplexity) use this to:
- Identify quotable statements
- Extract statistics and claims
- Understand author credibility
- Determine content freshness
- Verify facts against other sources

### Impact
- **+40% AI citations** for pages with facts.jsonld
- **36% boost** when combined with FAQPage schema
- **3.2x multiplier** for confident, quotable statements

### Input
- Website URL
- Crawled HTML content
- Extracted text content

### Output
- `facts.jsonld` file (JSON-LD format)
- Quality validation report
- Citation impact score (0-100)

---

## Architecture

### System Design
```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT: Website URL + HTML                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────────┐
         │   STEP 1: Content Extraction & NER      │
         │   - Parse HTML                          │
         │   - Extract text                        │
         │   - Named Entity Recognition            │
         │   - Metadata extraction                 │
         └─────────────┬───────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────────────┐
         │   STEP 2: Fact Extraction               │
         │   - Find statistics (numbers, dates)    │
         │   - Extract confident statements       │
         │   - Identify definitions                │
         │   - Extract primary answer              │
         │   - Find quotes                         │
         └─────────────┬───────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────────────┐
         │   STEP 3: Entity Linking                │
         │   - Link to Wikidata                    │
         │   - Resolve entity types                │
         │   - Build entity graph                  │
         └─────────────┬───────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────────────┐
         │   STEP 4: Schema Generation             │
         │   - Build author entity                 │
         │   - Build organization entity           │
         │   - Build article schema                │
         │   - Map facts to schema                 │
         └─────────────┬───────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────────────┐
         │   STEP 5: Validation                    │
         │   - Quality checks                      │
         │   - Conflict detection                  │
         │   - Completeness scoring                │
         │   - Issue reporting                     │
         └─────────────┬───────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────────────┐
         │   STEP 6: LLM Enhancement (Optional)    │
         │   - Improve weak facts                  │
         │   - Add missing context                 │
         │   - Enhance statements                  │
         └─────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT: facts.jsonld + Validation Report + Quality Score    │
└──────────────────────────────────────────────────────────────┘
```

---

## Pipeline Steps

### Step 1: Content Extraction & Named Entity Recognition

#### Input
```json
{
  "url": "https://example.com/article",
  "html": "<html>...</html>",
  "text": "Full extracted text content...",
  "metadata": {
    "title": "Page Title",
    "description": "Meta description"
  }
}
```

#### Process
1. Parse HTML to extract text
2. Remove boilerplate (navigation, ads, comments)
3. Run Named Entity Recognition (spaCy, Hugging Face)
4. Extract metadata (author, date, organization)

#### Output
```json
{
  "text": "Full cleaned text",
  "entities": {
    "PERSON": [
      {"text": "John Doe", "start": 0, "end": 8}
    ],
    "ORG": [
      {"text": "Acme Corp", "start": 20, "end": 29}
    ],
    "DATE": [
      {"text": "2025", "start": 50, "end": 54}
    ],
    "GPE": [
      {"text": "San Francisco", "start": 100, "end": 113}
    ]
  },
  "metadata": {
    "title": "How to Get Cited by AI",
    "author_name": "John Doe",
    "author_title": "AI SEO Specialist",
    "org_name": "Acme Corp",
    "publish_date": "2025-12-28",
    "last_updated": "2025-12-28"
  }
}
```

---

### Step 2: Fact Extraction

#### Input
Text content + entities from Step 1

#### Rules for Extraction

##### Rule 2A: Statistics & Numbers
```
Pattern: Contains digit, percentage, currency, or date
Example: "50% of SaaS founders struggle with churn"
Priority: HIGH (30-40% citation boost)
Min occurrences: 2+
```

##### Rule 2B: Confident Statements
```
Pattern: Uses strong verbs (is, causes, reduces) without weak modifiers
Strong verbs: is, causes, results in, leads to, reduces, increases
Weak modifiers: might, could, may, possibly, perhaps, seems

Example: "Context is the biggest challenge" (STRONG)
Example: "Context might be important" (WEAK - skip)
Priority: HIGH (3.2x citation multiplier)
Min confidence: 0.8+
```

##### Rule 2C: Definitions
```
Pattern: "X is/means/refers to Y"
Example: "GEO is Generative Engine Optimization"
Priority: MEDIUM-HIGH
Min occurrences: 1+
```

##### Rule 2D: Primary Answer
```
Pattern: First 2-3 sentences of page
Example: "To get cited by AI, use schema markup and quotable statements"
Priority: CRITICAL (first thing AI extracts)
Position: Always at start
```

##### Rule 2E: Quotable Statements
```
Pattern: Standalone statement that can be quoted directly
Example: "AI prioritizes fresh, authoritative sources"
Priority: HIGH (used in LLM citations)
Min length: 10 words
Max length: 150 words
```

#### Output
```json
{
  "facts": [
    {
      "id": "fact_001",
      "type": "statistic",
      "statement": "50% of websites lack proper AI-ready documentation",
      "original_text": "50% of websites lack proper AI-ready documentation according to recent surveys",
      "importance": "high",
      "confidence": 0.95,
      "source_position": {"start": 100, "end": 160},
      "entities_mentioned": ["websites", "documentation"],
      "supporting_evidence": "recent surveys"
    },
    {
      "id": "fact_002",
      "type": "claim",
      "statement": "Schema markup is critical for AI visibility",
      "confidence": 0.88,
      "has_weak_modifiers": false,
      "is_quotable": true,
      "importance": "high"
    },
    {
      "id": "fact_003",
      "type": "definition",
      "statement": "GEO (Generative Engine Optimization) is the practice of optimizing content for citation in AI-generated answers",
      "term": "GEO",
      "definition": "the practice of optimizing content for citation in AI-generated answers",
      "importance": "high"
    },
    {
      "id": "fact_004",
      "type": "primary_answer",
      "statement": "To get cited by AI, use JSON-LD schema, create quotable statements, and include statistics with dates",
      "position": "critical",
      "order": 1,
      "is_complete_answer": true
    }
  ],
  "statistics": {
    "total_facts": 4,
    "by_type": {
      "statistic": 1,
      "claim": 1,
      "definition": 1,
      "primary_answer": 1,
      "quote": 0
    },
    "avg_confidence": 0.91
  }
}
```

---

### Step 3: Entity Linking

#### Input
Facts + extracted entities from Steps 1-2

#### Process
1. For each entity mentioned in facts, find Wikidata match
2. Resolve entity type (Person, Organization, Place, etc.)
3. Build knowledge graph connections
4. Extract sameAs URIs (Wikipedia, LinkedIn, Twitter)

#### Output
```json
{
  "entities": {
    "e_001": {
      "text": "John Doe",
      "type": "Person",
      "wikidata_id": "Q12345678",
      "wikipedia_url": "https://en.wikipedia.org/wiki/John_Doe",
      "linkedin_url": "https://linkedin.com/in/johndoe",
      "twitter_url": "https://twitter.com/johndoe",
      "same_as": [
        "https://wikidata.org/wiki/Q12345678",
        "https://en.wikipedia.org/wiki/John_Doe"
      ],
      "mentions_in_facts": ["fact_001", "fact_002"]
    },
    "e_002": {
      "text": "Acme Corp",
      "type": "Organization",
      "wikidata_id": "Q87654321",
      "linkedin_url": "https://linkedin.com/company/acme-corp",
      "website": "https://acmecorp.com",
      "same_as": [
        "https://wikidata.org/wiki/Q87654321"
      ],
      "mentions_in_facts": ["fact_003"]
    }
  },
  "knowledge_graph": {
    "edges": [
      {
        "source": "e_001",
        "target": "e_002",
        "relation": "worksFor",
        "confidence": 0.92
      }
    ]
  }
}
```

---

### Step 4: Schema Generation

#### Input
Facts + entities + metadata from previous steps

#### Output (facts.jsonld)
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Article",
      "@id": "https://example.com/article#article",
      "url": "https://example.com/article",
      "name": "How to Get Cited by AI: Complete Guide",
      "description": "Step-by-step guide to optimizing content for AI citations",
      "headline": "How to Get Cited by AI",
      "image": "https://example.com/image.jpg",
      
      "author": {
        "@type": "Person",
        "@id": "https://example.com#author-john-doe",
        "name": "John Doe",
        "url": "https://example.com/authors/john-doe",
        "jobTitle": "AI SEO Specialist with 8 years experience",
        "email": "john@example.com",
        "affiliation": {
          "@type": "Organization",
          "@id": "https://example.com#org",
          "name": "Acme Corp"
        },
        "sameAs": [
          "https://www.linkedin.com/in/johndoe",
          "https://twitter.com/johndoe",
          "https://wikidata.org/wiki/Q12345678"
        ]
      },
      
      "publisher": {
        "@type": "Organization",
        "@id": "https://example.com#org",
        "name": "Acme Corp",
        "url": "https://example.com",
        "logo": "https://example.com/logo.png",
        "sameAs": [
          "https://www.linkedin.com/company/acme-corp",
          "https://twitter.com/acmecorp",
          "https://wikidata.org/wiki/Q87654321"
        ]
      },
      
      "datePublished": "2025-12-28T00:00:00Z",
      "dateModified": "2025-12-28T12:00:00Z",
      
      "mainEntity": {
        "@type": "Thing",
        "name": "AI Citation Optimization",
        "description": "Process of optimizing web content for citation by AI systems",
        "sameAs": "https://wikidata.org/wiki/Q99999999"
      },
      
      "mentions": [
        {
          "@type": "Thing",
          "name": "JSON-LD",
          "url": "https://json-ld.org",
          "sameAs": "https://wikidata.org/wiki/Q2894645"
        },
        {
          "@type": "Organization",
          "name": "OpenAI",
          "url": "https://openai.com",
          "sameAs": "https://wikidata.org/wiki/Q33971773"
        }
      ],
      
      "facts": [
        {
          "@type": "Fact",
          "@id": "https://example.com/article#fact-001",
          "type": "statistic",
          "statement": "50% of websites lack proper AI-ready documentation",
          "dateModified": "2025-12-28",
          "confidence": "high",
          "credibility": 0.95,
          "source": "recent surveys",
          "entities": ["websites", "documentation"]
        },
        {
          "@type": "Fact",
          "@id": "https://example.com/article#fact-002",
          "type": "claim",
          "statement": "Schema markup is critical for AI visibility",
          "dateModified": "2025-12-28",
          "confidence": "high",
          "credibility": 0.88,
          "isQuotable": true
        },
        {
          "@type": "Fact",
          "@id": "https://example.com/article#fact-003",
          "type": "definition",
          "statement": "GEO (Generative Engine Optimization) is the practice of optimizing content for citation in AI-generated answers",
          "dateModified": "2025-12-28",
          "confidence": "high",
          "term": "GEO"
        },
        {
          "@type": "Fact",
          "@id": "https://example.com/article#fact-004",
          "type": "primary_answer",
          "statement": "To get cited by AI, use JSON-LD schema, create quotable statements, and include statistics with dates",
          "dateModified": "2025-12-28",
          "confidence": "high",
          "position": "critical",
          "isComplete": true
        }
      ]
    }
  ]
}
```

---

### Step 5: Validation

#### Input
Generated facts.jsonld

#### Validation Rules

| Rule | Criterion | Pass Condition | Severity |
|------|-----------|----------------|----------|
| V1 | Author Present | `author.name` exists | HIGH |
| V2 | Author Credentials | `author.jobTitle` exists | HIGH |
| V3 | Organization Present | `publisher.name` exists | HIGH |
| V4 | Organization Links | `publisher.sameAs` has 2+ links | MEDIUM |
| V5 | Recent Date | `dateModified` < 90 days old | MEDIUM |
| V6 | Minimum Facts | `facts` array >= 3 items | HIGH |
| V7 | Statistics Count | >= 1 statistic type fact | MEDIUM |
| V8 | Primary Answer | >= 1 primary_answer type | HIGH |
| V9 | Fact Confidence | avg confidence >= 0.75 | MEDIUM |
| V10 | No Conflicts | No contradictory facts | HIGH |
| V11 | Valid JSON-LD | Passes schema.org validator | HIGH |
| V12 | Entity Linking | >= 2 entities linked | LOW |

#### Output
```json
{
  "validation": {
    "is_valid": true,
    "quality_score": 92,
    "issues": [],
    "warnings": [],
    "checks": {
      "V1_author_present": {
        "passed": true,
        "message": "Author 'John Doe' found"
      },
      "V2_author_credentials": {
        "passed": true,
        "message": "Job title 'AI SEO Specialist' present"
      },
      "V6_minimum_facts": {
        "passed": true,
        "message": "4 facts extracted (required: 3)",
        "actual": 4,
        "required": 3
      },
      "V7_statistics_count": {
        "passed": true,
        "message": "1 statistic found",
        "actual": 1,
        "required": 1
      }
    },
    "quality_breakdown": {
      "completeness": 95,
      "freshness": 100,
      "credibility": 88,
      "entity_linking": 75
    }
  }
}
```

---

### Step 6: LLM Enhancement (Optional)

#### When to Trigger
- Quality score < 75
- Missing critical facts
- Weak confidence scores
- Author credentials missing

#### Input to LLM
```
Content: [page text]
Current facts.jsonld: [JSON]
Issues: [list of validation issues]

Task: Improve facts.jsonld by:
1. Extracting 2-3 additional facts not found
2. Improving confidence scores for weak facts
3. Adding missing author credentials
4. Enhancing statement clarity

Output: Updated facts.jsonld
```

#### Output
Updated facts.jsonld with improved facts and higher quality scores

---

## Data Structures

### Fact Object
```json
{
  "id": "fact_001",
  "type": "statistic|claim|definition|primary_answer|quote",
  "statement": "The actual fact/statement",
  "original_text": "Original text from source (for verification)",
  "importance": "low|medium|high|critical",
  "confidence": 0.0-1.0,
  "credibility": 0.0-1.0,
  "source_position": {
    "start": 100,
    "end": 200
  },
  "entities_mentioned": ["entity1", "entity2"],
  "supporting_evidence": "optional evidence string",
  "is_quotable": true|false,
  "requires_update": false
}
```

### Entity Object
```json
{
  "id": "e_001",
  "text": "Entity Name",
  "type": "Person|Organization|Place|Thing",
  "wikidata_id": "Q12345678",
  "wikipedia_url": "https://...",
  "same_as": ["https://...", "https://..."],
  "confidence": 0.85,
  "mentions_in_facts": ["fact_001", "fact_003"]
}
```

### Validation Report
```json
{
  "is_valid": true|false,
  "quality_score": 0-100,
  "total_checks": 12,
  "passed_checks": 11,
  "failed_checks": 1,
  "issues": [
    {
      "rule": "V7",
      "severity": "MEDIUM",
      "message": "Only 1 statistic found, recommend 2+"
    }
  ],
  "warnings": [],
  "recommendations": []
}
```

---

## Implementation Details

### Dependencies
```python
# NER & Text Processing
spacy>=3.5.0
transformers>=4.30.0
nltk>=3.8

# JSON-LD & Schema
jsonschema>=4.17.0
rdflib>=6.2.0

# Entity Linking
wptools>=0.5.5
requests>=2.28.0

# LLM Integration (optional)
openai>=0.27.0  # or anthropic>=0.3.0, huggingface_hub>=0.14.0
```

### Configuration
```python
CONFIG = {
    "min_facts_required": 3,
    "min_statistics_required": 1,
    "min_confidence_threshold": 0.75,
    "max_content_age_days": 90,
    "entities_to_link": 2,
    "use_llm_enhancement": False,  # Set True for quality improvement
    "llm_model": "gpt-4-turbo-preview",  # or claude-3-opus
    "wikidata_lookup_enabled": True,
    "validate_against_schema_org": True,
    "generate_validation_report": True
}
```

---

## API Specification

### Main Function
```
POST /generate-facts-jsonld

Request:
{
  "url": "https://example.com/article",
  "html": "<html>...</html>",
  "text": "Extracted text...",
  "metadata": {
    "title": "Page Title",
    "author_name": "John Doe",
    "author_title": "AI SEO Specialist",
    "org_name": "Acme Corp",
    "publish_date": "2025-12-28",
    "last_updated": "2025-12-28"
  },
  "options": {
    "use_llm_enhancement": false,
    "validate_schema": true,
    "link_entities": true
  }
}

Response:
{
  "success": true,
  "facts_jsonld": {...},
  "validation": {...},
  "quality_score": 92,
  "estimated_citation_boost": "40%",
  "processing_time_ms": 2150,
  "file_url": "https://example.com/.well-known/facts.jsonld"
}
```

---

## Examples

### Example 1: Basic Article
**Input:** Simple blog post about AI SEO

**Output:**
- 5 facts extracted
- Quality score: 88/100
- Issues: 1 (add organization sameAs link)

### Example 2: Technical Documentation
**Input:** API documentation with examples and statistics

**Output:**
- 8 facts extracted
- Quality score: 94/100
- No issues

### Example 3: Product Page
**Input:** SaaS product page with features

**Output:**
- 4 facts extracted
- Quality score: 76/100
- Issues: 2 (missing author, add more statistics)
- LLM enhancement recommended

---

## Testing Checklist

- [ ] NER correctly identifies all entity types
- [ ] Statistics extraction finds all numbers/percentages
- [ ] Confident statement detection works accurately
- [ ] Definition extraction identifies all "X is Y" patterns
- [ ] Primary answer extraction gets first 2-3 sentences
- [ ] Schema generation produces valid JSON-LD
- [ ] Validation rules trigger correctly
- [ ] Wikidata linking works for known entities
- [ ] LLM enhancement improves weak facts
- [ ] Output validates against schema.org
- [ ] Quality score correlates with actual citation boost
- [ ] Processing time < 5 seconds per page

---

## Deployment Checklist

- [ ] All dependencies installed
- [ ] Configuration values set
- [ ] API endpoint secured (auth/rate limiting)
- [ ] Output directory has write permissions
- [ ] Wikidata API accessible
- [ ] LLM API keys configured (if using)
- [ ] Monitoring/logging enabled
- [ ] Error handling for network failures
- [ ] Cache implemented for repeated URLs
- [ ] Response validation in place