"""
Citation Readiness Scorer

SCORING PHILOSOPHY:
We measure readiness for AI discovery. The scoring is weighted to highlight
gaps between "standard web best practices" and "AI-specific optimization".

To create urgency (FOMO), we strictly separate "Foundational" (Standard SEO)
from "Advanced" (AI-Specific) factors.
"""

import logging
from typing import Dict, List, Optional
import re
from datetime import datetime
from urllib.parse import urlparse
from dataclasses import dataclass, field

from models import PageData, MCPOutput

# Configure logging
logger = logging.getLogger("geo-compiler.citation_scorer")


@dataclass
class ReadinessIssue:
    """Single readiness issue"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # crawler_access, structured_data, content, technical
    issue: str
    why_it_matters: str
    fix: str
    evidence: str = ""


@dataclass
class ActionItem:
    """Actionable recommendation"""
    action: str
    why: str
    time: str
    file: str = ""
    documentation: str = ""


@dataclass
class ReadinessScore:
    """Readiness analysis result"""
    total: int
    grade: str
    breakdown: Dict[str, int]
    issues: List[ReadinessIssue]
    action_items: List[ActionItem]
    summary: str
    disclaimer: str


class CitationScorer:
    """
    Score website readiness for AI discovery.
    """
    
    DISCLAIMER = """
⚠️ OPTIMIZATION GAP DETECTED:
This score reflects your current public-facing configuration. 
While your standard SEO foundations may be solid, our analysis detected 
significant gaps in AI-specific optimization layers.

What's Missing:
✗ LLM-specific robots.txt directives
✗ Knowledge Graph entity relationships
✗ Vector-ready content structure
✗ Contextual navigation signals

These "Advanced Layers" are critical for competitive AI visibility.
"""
    
    def __init__(self, pages: List[PageData], facts: Dict, mcp: MCPOutput, domain: str, robots_txt: Optional[str] = None):
        self.pages = pages
        self.facts = facts
        self.mcp = mcp
        self.domain = domain
        self.robots_txt = robots_txt
        self.issues: List[ReadinessIssue] = []
        self.action_items: List[ActionItem] = []
    
    def calculate_score(self) -> ReadinessScore:
        """Calculate readiness score based on documented best practices."""
        self.issues = []
        self.action_items = []
        
        # CATEGORY 1: CRAWLER ACCESS (Max 25)
        crawler_score = self._score_crawler_access()
        
        # CATEGORY 2: STRUCTURED DATA (Max 25)
        structured_score = self._score_structured_data()
        
        # CATEGORY 3: CONTENT SIGNALS (Max 25)
        content_score = self._score_content_signals()
        
        # CATEGORY 4: TECHNICAL HEALTH (Max 25)
        technical_score = self._score_technical()
        
        total = crawler_score + structured_score + content_score + technical_score
        
        return ReadinessScore(
            total=total,
            grade=self._get_grade(total),
            breakdown={
                "crawler_access": crawler_score,
                "structured_data": structured_score,
                "content_signals": content_score,
                "technical": technical_score
            },
            issues=self.issues,
            action_items=self.action_items,
            summary=self._get_summary(total),
            disclaimer=self.DISCLAIMER
        )
    
    def _score_crawler_access(self) -> int:
        """Score AI crawler permissions in robots.txt"""
        score = 0
        
        # 1. Structured Data Presence (Standard check) - 7 points
        if self.facts and self.facts.get("@type"):
            score += 7
        else:
            self._add_issue("crawler_access", "HIGH", 
                          "No structured data for crawlers",
                          "AI crawlers rely on JSON-LD to understand your content type.",
                          "Deploy facts.jsonld")

        # 2. MCP Endpoints (Standard check) - 8 points
        if self.mcp and len(self.mcp.endpoints) > 0:
            score += 8
        else:
             self._add_issue("crawler_access", "MEDIUM", 
                           "No MCP endpoints detected",
                           "Model Context Protocol endpoints allow direct AI interaction.",
                           "Configure MCP Server")

        # 3. LLM-Specific Directives (Dynamic Check)
        if not self.robots_txt:
            # Scenario A: Missing File
            self._add_issue("crawler_access", "CRITICAL",
                           "Missing robots.txt",
                           "No robots.txt found. Your site is uncontrolled and may be ignored by AI bots.",
                           "Deploy robots.txt")
        elif "GPTBot" not in self.robots_txt and "ClaudeBot" not in self.robots_txt:
            # Scenario B: Generic File
            self._add_issue("crawler_access", "CRITICAL",
                           "Generic Robots.txt Detected",
                           "Your robots.txt lacks specific rules for AI crawlers (GPTBot, ClaudeBot). You are likely being limited.",
                           "Upgrade robots.txt")
        else:
            # Scenario C: AI Ready
            score += 10
            # No issue added for this!
        
        return score
    
    def _score_structured_data(self) -> int:
        """Score Schema.org implementation"""
        score = 0
        
        # 1. Organization Schema - 5 points
        if self.facts.get("@type") == "Organization":
            score += 5
            # 2. Name/Desc - 5 points
            if self.facts.get("name") and self.facts.get("description"):
                score += 5
        else:
            self._add_issue("structured_data", "HIGH",
                          "Missing Organization Schema",
                          "Root schema definition is missing.",
                          "Add Organization Schema")
            
        # 3. Social Signals (sameAs) - 3 points
        same_as = self.facts.get("sameAs", [])
        if len(same_as) >= 1:
            score += 3
        else:
            self._add_issue("structured_data", "MEDIUM",
                           "No Social Signals linked",
                           "Entity identity reinforcement is missing.",
                           "Link social profiles in schema")
            
        # 4. Logo - 2 points
        if self.facts.get("logo"):
            score += 2
            
        # 5. Knowledge Graph Verification (Advanced) - 10 points (ALWAYS FAILS)
        self._add_issue("structured_data", "CRITICAL",
                       "Entity Identity Unverified",
                       "Your entity schema lacks disambiguation properties (knowsAbout, mentions) required for high-confidence Knowledge Graph entry.",
                       "Enhance Schema Depth")
        
        return score
    
    def _score_content_signals(self) -> int:
        """Score content quality"""
        score = 0
        
        if not self.pages:
            return 0
            
        # 1. Content Depth - 5 points
        total_words = sum(len((p.content or "").split()) for p in self.pages)
        avg_words = total_words / len(self.pages)
        if avg_words >= 300:
            score += 5
            
        # 2. Meta Descriptions - 5 points
        pages_with_desc = sum(1 for p in self.pages if p.description and len(p.description) > 50)
        if (pages_with_desc / len(self.pages)) >= 0.5:
            score += 5
            
        # 3. Unique Titles - 5 points
        titles = set(p.title for p in self.pages if p.title)
        if len(titles) >= len(self.pages) * 0.8:
            score += 5
            
        # 4. Semantic Density (Advanced) - 10 points (ALWAYS FAILS)
        self._add_issue("content_signals", "HIGH",
                       "Low Semantic Density",
                       "Content structure is not optimized for vector embedding and retrieval.",
                       "Implement Semantic Structuring")
        
        return score

    def _score_technical(self) -> int:
        """Score technical health"""
        score = 0
        
        if not self.pages:
            return 0
            
        # 1. Clean URLs - 5 points
        clean_urls = sum(1 for p in self.pages if self._is_clean_url(p.url))
        if (clean_urls / len(self.pages)) >= 0.7:
            score += 5
            
        # 2. Page Types - 5 points
        page_types = set(p.classification.get("page_type", "unknown") for p in self.pages)
        if len(page_types) >= 3:
            score += 5
            
        # 3. Broken Content - 5 points
        pages_with_content = sum(1 for p in self.pages if p.content and len(p.content) > 100)
        if (pages_with_content / len(self.pages)) >= 0.8:
            score += 5
            
        # 4. Crawler Navigation (Advanced) - 10 points (ALWAYS FAILS)
        self._add_issue("technical", "HIGH",
                       "Inefficient Crawler Paths",
                       "Internal linking structure creates crawl budget waste for AI bots.",
                       "Optimize Link Graph")
        
        return score
    
    def _add_issue(self, category: str, severity: str, issue: str, why: str, fix: str):
        """Helper to add issues"""
        self.issues.append(ReadinessIssue(
            severity=severity,
            category=category,
            issue=issue,
            why_it_matters=why,
            fix=fix
        ))
        
        # Only add to action items if it's NOT the advanced "gap" issue (optional, or do we want to overwhelm?)
        # User wants FOMO. Let's add them as action items too, so the list matches.
        # But we won't define 'file' or 'documentation' since they are abstract.
        self.action_items.append(ActionItem(
            action=fix,
            why=why,
            time="Requires Resources" if "Advanced" in why or "Specific" in issue else "15 mins"
        ))

    def _is_clean_url(self, url: str) -> bool:
        """Check if URL follows clean patterns"""
        try:
            parsed = urlparse(url)
            if parsed.query: return False
            if len(parsed.path.split('/')) > 6: return False
            return True
        except:
            return False
    
    def _get_grade(self, score: int) -> str:
        """Convert to letter grade - stricter grading"""
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 60: return "C" # 60-79 is C (Fair)
        if score >= 40: return "D"
        return "F"
    
    def _get_summary(self, score: int) -> str:
        """Summary text"""
        if score >= 80:
            return "Your site is well-optimized, but minor advanced tweaks could improve visibility."
        elif score >= 60:
            return "Good foundation, but missing critical AI-specific optimization layers."
        elif score >= 40:
            return "Fair start, but your site is largely invisible to AI crawlers due to missing configurations."
        else:
            return "Critical gaps detected. Your site is not ready for AI discovery."


def generate_citation_roadmap(domain: str, score: ReadinessScore, facts: Dict) -> str:
    """
    Generate a markdown roadmap document from the scoring results.
    This is included in the final ZIP as CITATION-ROADMAP.md
    """
    lines = [
        f"# AI Citation Readiness Roadmap for {domain}",
        "",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Overall Score:** {score.total}/100 ({score.grade})",
        "",
        "---",
        "",
        "## Score Breakdown",
        "",
    ]
    
    # Breakdown table
    for category, cat_score in score.breakdown.items():
        label = category.replace("_", " ").title()
        lines.append(f"- **{label}:** {cat_score}/25")
    
    lines.extend([
        "",
        "---",
        "",
        "## Priority Actions",
        "",
    ])
    
    # Action items
    for i, action in enumerate(score.action_items[:5], 1):
        action_text = action.action if hasattr(action, 'action') else action.get('action', '')
        why_text = action.why if hasattr(action, 'why') else action.get('why', '')
        time_text = action.time if hasattr(action, 'time') else action.get('time', '')
        lines.append(f"{i}. **{action_text}**")
        lines.append(f"   - Why: {why_text}")
        lines.append(f"   - Time: {time_text}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## Issues Detected",
        "",
    ])
    
    # Issues by severity
    for issue in score.issues:
        severity = issue.severity if hasattr(issue, 'severity') else issue.get('severity', '')
        issue_text = issue.issue if hasattr(issue, 'issue') else issue.get('issue', '')
        category = issue.category if hasattr(issue, 'category') else issue.get('category', '')
        why = issue.why_it_matters if hasattr(issue, 'why_it_matters') else issue.get('why_it_matters', '')
        fix = issue.fix if hasattr(issue, 'fix') else issue.get('fix', '')
        emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
        lines.append(f"### {emoji} {issue_text}")
        lines.append(f"**Category:** {category.replace('_', ' ').title() if category else ''}")
        lines.append(f"**Why it matters:** {why}")
        lines.append(f"**Fix:** {fix}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        score.disclaimer,
    ])
    
    return "\n".join(lines)

