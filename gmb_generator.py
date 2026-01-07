"""
CiteKit - GMB Optimization Pack Generator
Generates high-value, SEO-optimized content for Google My Business profiles.
Designed to deliver immediate ROI ($600/mo agency value) by automating manual SEO tasks.
"""

import logging
from typing import List, Dict, Any
from collections import Counter
import re
from datetime import datetime

from models import PageData
from facts_generator import ExtractedFact, FactType

logger = logging.getLogger("geo-compiler.gmb_generator")

class GMBGenerator:
    """
    Generates a complete Google My Business optimization pack.
    Uses extracted facts and page content to create personalized, high-value assets.
    """

    def __init__(self, facts: List[ExtractedFact], pages: List[PageData], metadata: Dict[str, Any]):
        self.facts = facts
        self.pages = pages
        self.metadata = metadata
        self.org_name = metadata.get('org_name', 'Our Business')
        self.domain = metadata.get('domain', 'website.com')

    def generate_kit(self) -> Dict[str, str]:
        """
        Generate all GMB assets.
        Returns a dict mapping filenames to content.
        """
        return {
            "business_bio.txt": self.generate_bio(),
            "8_optimized_posts.md": self.generate_posts_content(),
            "local_keywords_strategy.md": self.generate_keyword_strategy(),
            "review_response_templates.md": self.generate_review_responses(),
            "services_setup.txt": self.generate_services_attributes()
        }

    def generate_bio(self) -> str:
        """
        Generates a conversion-focused 750-character Business Bio.
        Focus: Trust, Authority, Clear Services, Call to Action.
        """
        # 1. Gather Claims (Trust Signals)
        claims = [f.statement for f in self.facts if f.type == FactType.CLAIM and f.importance.value in ['high', 'critical']]
        top_claims = claims[:2] if claims else ["We provide top-quality service.", "Customer satisfaction is our priority."]
        
        # 2. Identify Services
        topics = self._extract_top_topics(limit=5)
        service_str = ", ".join(topics)

        # 3. Construct Bio
        bio = f"""{self.org_name}
Professional {topics[0] if topics else 'service'} provider.

WHO WE ARE:
{top_claims[0]} {top_claims[1] if len(top_claims) > 1 else ''}

WHAT WE OFFER:
Specializing in {service_str}. We deliver reliable, high-quality solutions tailored to your needs.

WHY CHOOSE US:
✅ Experienced Team
✅ Satisfaction Guaranteed
✅ Local Expertise

Visit our website at {self.domain} to learn more.

📞 CALL NOW for a consultation!
"""
        # Ensure it fits GMB limit (750 chars)
        if len(bio) > 750:
            bio = bio[:747] + "..."
            
        return bio

    def generate_posts_content(self) -> str:
        """
        Generates 8 ready-to-post GMB updates.
        Types: Educational, Promotional, Behind-the-Scenes (simulated), Social Proof.
        """
        posts = []
        
        # Helper to format a post
        def format_post(title, body, cta_type="Call Now"):
            return f"### 📝 Post: {title}\n\n**Caption:**\n{body}\n\n**Button:** {cta_type}\n**Image Idea:** {title} visual\n\n---\n"

        # 1. Statistic/Fact Posts
        stats = [f for f in self.facts if f.type == FactType.STATISTIC]
        for i, stat in enumerate(stats[:3]):
            posts.append(format_post(
                f"Did you know? ({i+1})",
                f"Did you know? {stat.statement}\n\nTrust the experts at {self.org_name} for data-driven results.\n\n#LinkInBio #{self.org_name.replace(' ', '')} #ExpertTips",
                "Learn More"
            ))

        # 2. Quote/Testimonial Posts (simulated from extracted quotes or generically framed)
        quotes = [f for f in self.facts if f.type == FactType.QUOTE]
        for i, quote in enumerate(quotes[:2]):
             posts.append(format_post(
                f"Expert Insight ({i+1})",
                f"\"{quote.statement}\"\n\nWe believe in quality and transparency. Experience the difference with us.\n\n📍 Visit us today!",
                "Book Online"
            ))

        # 3. Service Highlight Posts (from Topics)
        topics = self._extract_top_topics(limit=3)
        for topic in topics:
             posts.append(format_post(
                f"Service Spotlight: {topic}",
                f"Looking for {topic}? We have got you covered! \n\n{self.org_name} offers premium {topic} services designed to meet your needs.\n\n👇 Click below to get started!",
                "Sign Up"
            ))

        # Fill remaining if needed
        while len(posts) < 8:
            posts.append(format_post(
                "Customer Appreciation",
                f"Thank you to our amazing community for choosing {self.org_name}! We love serving you.\n\nHave questions? We are here to help.\n\n📞 Contact us today!",
                "Call Now"
            ))

        return "# 📅 8-Week GMB Content Calendar\n\nCopy and paste these posts to your Google Business Profile to boost visibility.\n\n" + "\n".join(posts)

    def generate_keyword_strategy(self) -> str:
        """
        Extracts high-value local keywords.
        """
        topics = self._extract_top_topics(limit=20)
        
        # Heuristic: Add "near me", "service", etc.
        keywords = []
        for t in topics:
            keywords.append(f"{t}")
            keywords.append(f"{t} near me")
            keywords.append(f"best {t}")
            keywords.append(f"{t} service")
            keywords.append(f"{t} expert")
        
        md = f"""# 🔑 Local SEO Keyword Strategy for {self.org_name}

These keywords are extracted from your actual content and optimized for Local Search intent.

## Top High-Intent Keywords
Use these in your GMB Services, Bio, and Post captions.

| Keyword | Intent | Usage Tip |
|---------|--------|-----------|
"""
        for kw in keywords[:15]:
            md += f"| {kw} | Transactional | Add to Service Description |\n"
            
        md += "\n\n## 💡 how to use\n1. Add the 'Top' keywords to your GMB 'Services' tab.\n2. Use 'near me' variations in your weekly posts.\n3. Ask reviewers to mention the specific service they received."
        
        return md

    def generate_review_responses(self) -> str:
        """
        Generates professional templates for responding to reviews.
        """
        return f"""# 💬 GMB Review Response Templates for {self.org_name}

Respond to reviews within 24 hours to boost your SEO ranking.

## ⭐⭐⭐⭐⭐ 5-Star Reviews (Positive)

**Option 1 (Standard):**
"Hi [Name], thank you so much for the 5-star review! We are thrilled to hear you had a great experience with {self.org_name}. We look forward to serving you again soon!"

**Option 2 (Service Specific):**
"Thanks [Name]! We are glad you liked our service. Our team works hard to deliver the best quality. We appreciate your support!"

## ⭐⭐⭐ 3-Star Reviews (Neutral)

**Template:**
"Hi [Name], thank you for your feedback. We aim for 5-star service and it sounds like we missed the mark. Please contact us directly at our office so we can make it right."

## ⭐ 1-Star Reviews (Negative)

**Template:**
"Hi [Name], we take this feedback seriously. We would like to understand what happened and resolve this issue immediately. Please call our manager directly. We value your business and hope to fix this."
"""

    def generate_services_attributes(self) -> str:
        """
        Formats a list of services for GMB.
        """
        topics = self._extract_top_topics(limit=15)
        
        txt = f"GMB SERVICES LIST FOR: {self.org_name}\n\n"
        txt += "Copy these exact terms into your GMB 'Services' tab:\n\n"
        
        for t in topics:
            txt += f"- {t}\n"
            
        txt += "\n\nCategory Suggestions:\n"
        txt += f"- {topics[0] if topics else 'Service'} Provider\n"
        txt += f"- {topics[1] if len(topics)>1 else 'Professional'} Service\n"
        
        return txt

    def _extract_top_topics(self, limit: int = 10) -> List[str]:
        """
        Extracts top topics from page classification data.
        """
        all_topics = []
        for p in self.pages:
            # Check if topics exist in classification
            topics = p.classification.get('topics', [])
            all_topics.extend(topics)
            
            # Also use headings if topics are sparse
            if not topics and p.headings:
                 # Simple heuristic: H1s are usually topics
                 h1s = [h.replace('# ', '') for h in p.headings if h.startswith('# ')]
                 all_topics.extend(h1s)

        # Count and sort
        counter = Counter(all_topics)
        # Filter out extremely short or common stop words if necessary (basic filter)
        valid_topics = [t for t, c in counter.most_common(50) if len(t) > 3]
        
        return valid_topics[:limit]
