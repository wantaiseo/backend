# facts.jsonld - Developer Briefing One-Pager

## What is facts.jsonld?
A machine-readable JSON-LD file that extracts valuable facts from website content for AI systems (ChatGPT, Claude, Gemini, Perplexity) to cite.

**Impact:** +40% AI citations | **Quality Factor:** Critical for AI discoverability

---

## 6-Step Implementation Pipeline

```
┌──────────────────┐
│  1. NER Extract  │  ← Use spaCy to identify entities + metadata
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  2. Extract      │  ← Find 5 fact types:
│     Facts        │     • Statistics (numbers + dates)
└────────┬─────────┘     • Claims (confident statements)
         │               • Definitions (X is Y)
         ▼               • Primary Answer (first 2-3 sentences)
┌──────────────────┐     • Quotes (quotable statements)
│  3. Generate     │
│  JSON-LD Schema  │  ← Map facts to schema.org Article
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  4. Validate     │  ← Run 12 validation rules
│  (12 Rules)      │     Calculate quality score (0-100)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. Entity Link   │  ← Connect to Wikidata
│ (Optional)       │     Adds credibility
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  6. Output       │  ← Save facts.jsonld file
│  facts.jsonld    │     + Validation report
└──────────────────┘
```

---

## The 5 Fact Types to Extract

| Type | Pattern | Example | Impact |
|------|---------|---------|--------|
| **Statistics** | Numbers, %, dates | "50% of sites lack documentation" | +30-40% |
| **Claims** | Strong verbs, no weak modifiers | "Context is the biggest challenge" | 3.2x multiplier |
| **Definitions** | "X is Y" pattern | "GEO is Generative Engine Optimization" | High priority |
| **Primary Answer** | First 2-3 sentences | "To get cited, use schema + quotes + stats" | CRITICAL |
| **Quotes** | Standalone statements | "AI prioritizes fresh, authoritative sources" | High priority |

---

## The 12 Validation Rules

```
✓ V1  Author present
✓ V2  Author has credentials
✓ V3  Organization present
✓ V4  Organization has sameAs links (2+)
✓ V5  Content < 90 days old
✓ V6  Minimum 3 facts extracted
✓ V7  At least 1 statistic
✓ V8  Primary answer present
✓ V9  Average confidence >= 0.75
✓ V10 No conflicting facts
✓ V11 Valid JSON-LD (schema.org)
✓ V12 Entities linked to Wikidata (2+)
```

**Quality Score:** Points for each passed rule  
**Pass/Fail:** Quality >= 70 is deployable

---

## Key Code Functions

```python
# 1. Extract entities + metadata
extract_entities_and_metadata(html_text, url)
→ Returns: {entities, metadata}

# 2. Find facts (5 types)
extract_facts(text)
→ Returns: [fact1, fact2, fact3, ...]

# 3. Generate schema
generate_facts_jsonld(facts, metadata)
→ Returns: {JSON-LD schema}

# 4. Validate
validate_facts_jsonld(schema)
→ Returns: {is_valid, quality_score, issues}

# 5. Link entities
link_entities_to_wikidata(schema)
→ Returns: {schema with wikidata links}

# 6. Output
output_facts_jsonld(schema)
→ Returns: facts.jsonld file + report
```

---

## API Specification

```
POST /api/v1/generate-facts-jsonld

INPUT:
{
  "url": "https://example.com/article",
  "html": "<html>...</html>",
  "metadata": {
    "author": "John Doe",
    "author_title": "AI Specialist",
    "org": "Acme Corp"
  }
}

OUTPUT:
{
  "success": true,
  "facts_jsonld": {...},
  "quality_score": 92,
  "is_valid": true,
  "estimated_citation_boost": "40%",
  "processing_time_ms": 2150
}
```

**Response Time Target:** < 5 seconds (p95)

---

## Quality Score Breakdown

```
Author present:          +20 points
Author credentials:      +15 points
Organization:            +15 points
Organization links:      +10 points
Content freshness:       +10 points
Minimum facts:           +10 points
Statistics present:      +5 points
High confidence:         +5 points
No conflicts:            +5 points
Entity linking:          +5 points
Valid JSON-LD:           +5 points
─────────────────────────
TOTAL:                   100 points
```

---

## What Makes facts.jsonld "Valuable"

✅ **Statistics with dates** (30-40% more likely to be cited)  
✅ **Quotable, confident statements** (3.2x multiplier)  
✅ **Author credentials** (25% boost)  
✅ **Fresh content** (days/weeks, not months)  
✅ **Entity linking** (credibility signal)  
✅ **No conflicting claims** (AI trusts consistent sources)  

❌ **What hurts citations:**
- Weak language: "might", "could", "may"
- Missing author info
- Old content (>90 days)
- Too few facts (<3)
- No statistics
- Conflicting statements

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1** | 2 weeks | NER + fact extraction (statistics, claims, definitions) |
| **Phase 2** | 1.5 weeks | JSON-LD schema generation + validation engine |
| **Phase 3** | 1.5 weeks | Entity linking + LLM enhancement (optional) |
| **Phase 4** | 1 week | API deployment + optimization |

**Total:** 4-6 weeks for production-ready implementation

---

## Success Criteria

- [x] Generate valid facts.jsonld for 95%+ of pages
- [x] Quality score > 85 for 70%+ of pages
- [x] Response time < 5 seconds (p95)
- [x] Extract 3+ facts per page 90% of the time
- [x] All validation rules implemented
- [x] Schema.org validator gives 0 errors
- [x] Entity linking works for 80%+ of entities
- [x] 85%+ test coverage

---

## Critical Success Factors

1. **Fact Extraction Accuracy** - This is the core. Accuracy directly impacts citation boost.

2. **Validation Strictness** - Quality gates must filter low-quality output or it hurts credibility.

3. **Performance** - Must be < 5 seconds or users will abandon.

4. **Error Handling** - If author extraction fails, don't fail the whole pipeline.

5. **Entity Disambiguation** - Wikidata linking is what separates "good" from "great".

---

## Documentation Package

You're getting 3 complementary documents:

1. **facts-jsonld-generation-spec.md** (Technical Specification)
   - 15-20 pages, detailed architecture, all rules
   - Use for: Code review, detailed reference

2. **facts-jsonld-json-prompt.json** (Requirements Document)
   - 8-10 pages, 9 functional requirements, 6 non-functional
   - Use for: Task assignment, progress tracking, QA

3. **facts-jsonld-quick-reference.md** (Implementation Guide)
   - 5-8 pages, copy-paste code, function templates
   - Use for: Active development, quick lookups

---

## Dependencies

```bash
pip install spacy>=3.5.0          # NER
pip install transformers>=4.30.0  # Embeddings
pip install nltk>=3.8             # Text processing
pip install requests>=2.28.0      # HTTP
pip install wptools>=0.5.5        # Wikidata
pip install jsonschema>=4.17.0    # Validation
pip install fastapi>=0.95.0       # API
pip install pytest>=7.0.0         # Testing

# Download model
python -m spacy download en_core_web_lg
```

---

## How to Brief Developer

1. **Show them this one-pager** (5 minutes)
2. **Hand them facts-jsonld-quick-reference.md** (start coding)
3. **Reference facts-jsonld-generation-spec.md** (for details)
4. **Track against facts-jsonld-json-prompt.json** (requirements)

---

## Expected Deliverables

✅ Python library for facts.jsonld generation  
✅ REST API endpoint  
✅ CLI tool (optional)  
✅ Full test suite (85%+ coverage)  
✅ API documentation  
✅ Deployment guide  

---

## Questions to Ask Developer

- Can we hit < 5 second response time?
- What spaCy model accuracy do we get (target: 90%)?
- Can we calibrate quality score to match real citation boost?
- How do we handle missing metadata gracefully?
- Should we cache Wikidata lookups?
- What's our strategy if LLM enhancement is unavailable?

---

## Go-Live Checklist

- [ ] All code tested and reviewed
- [ ] Performance benchmarks met (< 5 sec)
- [ ] Schema.org validation: 0 errors
- [ ] Quality score calibrated against real data
- [ ] Monitoring and logging enabled
- [ ] Rate limiting configured
- [ ] Error handling complete
- [ ] Documentation complete
- [ ] A/B test ready for citation boost measurement

---

**Start Date:** [Date]  
**Target Completion:** [Date + 4-6 weeks]  
**Status:** Ready for development handoff  
**Questions?** Review the 3 documentation files or ask the spec team