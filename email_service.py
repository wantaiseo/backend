"""
CiteKit Email Service
Handles transactional emails using Mailgun

Setup:
1. Create account at https://mailgun.com
2. Get API key from dashboard (Settings -> API Keys)
3. Get sandbox domain or verify your own domain
4. Add MAILGUN_API_KEY and MAILGUN_DOMAIN to .env
"""

import os
import requests
from typing import Optional
from config import get_settings


class EmailService:
    """Email service using Mailgun API"""
    
    def __init__(self):
        self.api_key = os.getenv("MAILGUN_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")  # e.g., sandbox123.mailgun.org or your domain
        self.from_email = os.getenv("EMAIL_FROM", "CiteKit <noreply@citekit.com>")
        self.enabled = bool(self.api_key and self.domain)
        
        # Mailgun API endpoint (use EU endpoint if needed)
        self.api_base = os.getenv("MAILGUN_API_BASE", "https://api.mailgun.net/v3")
        
        if not self.enabled:
            print("⚠️ Email service disabled: MAILGUN_API_KEY or MAILGUN_DOMAIN not configured")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email. Returns True if successful."""
        if not self.enabled:
            print(f"📧 [DRY RUN] Would send to {to_email}: {subject}")
            return False
        
        try:
            url = f"{self.api_base}/{self.domain}/messages"
            
            data = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            
            if text_content:
                data["text"] = text_content
            
            response = requests.post(
                url,
                auth=("api", self.api_key),
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Email sent to {to_email}: {result.get('id', 'success')}")
                return True
            else:
                print(f"❌ Mailgun error: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def send_payment_confirmation(
        self,
        to_email: str,
        job_id: str,
        domain: str,
        download_url: str,
        geo_score: Optional[int] = None
    ) -> bool:
        """Send payment confirmation with download link"""
        
        score_text = f"GEO Score: {geo_score}/100" if geo_score else ""
        
        # Professional subject line (no emojis to avoid spam filters)
        subject = f"Your CiteKit Package for {domain} is Ready"
        
        # Simpler, professional HTML (less likely to trigger spam)
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    
    <h2 style="color: #333;">Your CiteKit Package is Ready</h2>
    
    <p>Hi,</p>
    
    <p>Your GEO optimization package for <strong>{domain}</strong> has been generated and is ready for download.</p>
    
    {f'<p><strong>{score_text}</strong></p>' if score_text else ''}
    
    <p><strong>What's included:</strong></p>
    <ul>
        <li>llms.txt - AI-optimized content summary</li>
        <li>facts.jsonld - Structured facts for citations</li>
        <li>mcp.json - Model Context Protocol configuration</li>
        <li>robots.txt - AI crawler directives</li>
        <li>Audit Report - Detailed SEO analysis</li>
    </ul>
    
    <p>
        <a href="{download_url}" style="display: inline-block; background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Download Package</a>
    </p>
    
    <p><strong>Next steps:</strong></p>
    <ol>
        <li>Download and extract the ZIP file</li>
        <li>Upload the files to your website's root directory</li>
        <li>Verify by visiting: {domain}/llms.txt</li>
    </ol>
    
    <p>If you have any questions, simply reply to this email.</p>
    
    <p>Thank you for using CiteKit.</p>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #666;">
        Reference: {job_id}<br>
        You received this email because you purchased a CiteKit package.
    </p>
</body>
</html>
        """
        
        # Plain text version (important for deliverability)
        text_content = f"""Your CiteKit Package is Ready

Hi,

Your GEO optimization package for {domain} has been generated and is ready for download.

{score_text}

Download your package here:
{download_url}

What's included:
- llms.txt - AI-optimized content summary
- facts.jsonld - Structured facts for citations
- mcp.json - Model Context Protocol configuration
- robots.txt - AI crawler directives
- Audit Report - Detailed SEO analysis

Next steps:
1. Download and extract the ZIP file
2. Upload the files to your website's root directory
3. Verify by visiting: {domain}/llms.txt

If you have any questions, simply reply to this email.

Thank you for using CiteKit.

---
Reference: {job_id}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
