"""
CiteKit Email Service
Comprehensive transactional email system using Mailgun

Features:
- Welcome emails with subscription
- Payment confirmation with invoice
- Download links
- Unsubscribe management
"""

import os
import requests
import hashlib
import hmac
from datetime import datetime
from typing import Optional
from config import get_settings


class EmailService:
    """Email service using Mailgun API"""
    
    def __init__(self):
        self.api_key = os.getenv("MAILGUN_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")
        self.from_email = os.getenv("EMAIL_FROM", "CiteKit <hello@citekit.com>")
        self.enabled = bool(self.api_key and self.domain)
        
        # Mailgun API endpoint
        self.api_base = os.getenv("MAILGUN_API_BASE", "https://api.mailgun.net/v3")
        
        # Frontend URL for unsubscribe links
        settings = get_settings()
        self.frontend_url = settings.frontend_url or "https://citekit.com"
        
        if not self.enabled:
            print("⚠️ Email service disabled: MAILGUN_API_KEY or MAILGUN_DOMAIN not configured")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        tags: list = None
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
            
            if tags:
                data["o:tag"] = tags
            
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

    def generate_unsubscribe_token(self, email: str) -> str:
        """Generate a secure unsubscribe token for an email"""
        secret = os.getenv("MAILGUN_API_KEY", "default-secret")
        token = hmac.new(
            secret.encode(),
            email.lower().encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        return token

    def get_unsubscribe_url(self, email: str) -> str:
        """Get the unsubscribe URL for an email"""
        token = self.generate_unsubscribe_token(email)
        return f"{self.frontend_url}/unsubscribe?email={email}&token={token}"

    def verify_unsubscribe_token(self, email: str, token: str) -> bool:
        """Verify an unsubscribe token is valid"""
        expected_token = self.generate_unsubscribe_token(email)
        return hmac.compare_digest(token, expected_token)

    # ============================================
    # EMAIL TEMPLATES
    # ============================================

    def _get_email_wrapper(self, content: str, show_unsubscribe: bool = True, email: str = None) -> str:
        """Wrap content in a styled email template"""
        unsubscribe_section = ""
        if show_unsubscribe and email:
            unsubscribe_url = self.get_unsubscribe_url(email)
            unsubscribe_section = f"""
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                <p style="font-size: 11px; color: #888; margin: 0;">
                    You're receiving this because you signed up for CiteKit.<br>
                    <a href="{unsubscribe_url}" style="color: #888; text-decoration: underline;">Unsubscribe from marketing emails</a>
                </p>
            </div>
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CiteKit</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 0; background-color: #f9f9f8;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); padding: 30px 40px; text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">
            CiteKit
        </h1>
        <p style="margin: 5px 0 0 0; color: #888; font-size: 12px;">Make your website AI-readable</p>
    </div>
    
    <!-- Content -->
    <div style="background: #ffffff; padding: 40px; border: 1px solid #eee; border-top: none;">
        {content}
        {unsubscribe_section}
    </div>
    
    <!-- Footer -->
    <div style="padding: 20px 40px; text-align: center; background: #fafafa; border: 1px solid #eee; border-top: none;">
        <p style="font-size: 11px; color: #888; margin: 0;">
            © {datetime.now().year} CiteKit by Jayso Labs Private Limited<br>
            <a href="{self.frontend_url}/privacy" style="color: #666;">Privacy Policy</a> · 
            <a href="{self.frontend_url}/terms" style="color: #666;">Terms of Service</a>
        </p>
    </div>
</body>
</html>
        """

    def send_welcome_email(self, to_email: str, user_name: str = None) -> bool:
        """Send welcome email after signup"""
        
        name = user_name or to_email.split('@')[0].title()
        
        content = f"""
        <h2 style="color: #1a1a1a; margin: 0 0 20px 0; font-size: 24px;">Welcome to CiteKit, {name}! 🎉</h2>
        
        <p style="color: #444; font-size: 16px; margin-bottom: 25px;">
            You've just taken the first step to making your website discoverable by AI systems like ChatGPT, Claude, Perplexity, and more.
        </p>
        
        <p style="color: #444; font-size: 16px; margin-bottom: 25px;">
            <strong>Here's what you can do now:</strong>
        </p>
        
        <ul style="color: #444; font-size: 15px; padding-left: 20px; margin-bottom: 30px;">
            <li style="margin-bottom: 10px;">🔍 <strong>Audit your website</strong> – Enter any URL to analyze its AI-readability</li>
            <li style="margin-bottom: 10px;">📦 <strong>Generate your kit</strong> – Get llms.txt, mcp.json, and Schema.org files</li>
            <li style="margin-bottom: 10px;">🚀 <strong>Deploy and verify</strong> – Follow our step-by-step guide to go live</li>
        </ul>
        
        <div style="text-align: center; margin: 35px 0;">
            <a href="{self.frontend_url}/dashboard" 
               style="display: inline-block; background: #1a1a1a; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                Go to Dashboard →
            </a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
            <strong>💡 Quick Tip:</strong> For best results, run audits on your main domain (example.com) rather than specific pages. Our crawler will automatically discover and analyze your important content.
        </p>
        
        <p style="color: #666; font-size: 14px;">
            Questions? Just reply to this email – we read and respond to every message.
        </p>
        
        <p style="color: #1a1a1a; font-size: 15px; margin-top: 25px;">
            – The CiteKit Team
        </p>
        """
        
        html_content = self._get_email_wrapper(content, show_unsubscribe=True, email=to_email)
        
        text_content = f"""
Welcome to CiteKit, {name}!

You've just taken the first step to making your website discoverable by AI systems like ChatGPT, Claude, Perplexity, and more.

Here's what you can do now:
- Audit your website – Enter any URL to analyze its AI-readability
- Generate your kit – Get llms.txt, mcp.json, and Schema.org files  
- Deploy and verify – Follow our step-by-step guide to go live

Get started: {self.frontend_url}/dashboard

Quick Tip: For best results, run audits on your main domain rather than specific pages.

Questions? Just reply to this email – we read and respond to every message.

– The CiteKit Team
        """
        
        return self.send_email(
            to_email=to_email,
            subject="Welcome to CiteKit – Let's make your site AI-ready 🚀",
            html_content=html_content,
            text_content=text_content,
            tags=["welcome", "onboarding"]
        )

    def send_payment_confirmation(
        self,
        to_email: str,
        job_id: str,
        domain: str,
        download_url: str,
        payment_id: str = None,
        amount_paise: int = 84000,
        currency: str = "INR",
        geo_score: Optional[int] = None
    ) -> bool:
        """Send payment confirmation with invoice and download link"""
        
        # Format amount
        if currency == "INR":
            amount_display = f"₹{amount_paise / 100:.2f}"
            # GST breakdown (18% included in price)
            base_amount = amount_paise / 118 * 100
            gst_amount = amount_paise - base_amount
            gst_display = f"₹{gst_amount / 100:.2f}"
            base_display = f"₹{base_amount / 100:.2f}"
        else:
            amount_display = f"${amount_paise / 100:.2f}"
            base_display = amount_display
            gst_display = None
        
        # Generate invoice number
        invoice_date = datetime.now()
        invoice_number = f"CK-{invoice_date.strftime('%Y%m%d')}-{(payment_id or job_id)[-6:].upper()}"
        
        score_badge = ""
        if geo_score is not None:
            color = "#10b981" if geo_score >= 70 else "#f59e0b" if geo_score >= 40 else "#ef4444"
            score_badge = f"""
            <div style="text-align: center; margin: 20px 0;">
                <div style="display: inline-block; background: {color}15; border: 2px solid {color}; border-radius: 12px; padding: 15px 25px;">
                    <span style="font-size: 32px; font-weight: 800; color: {color};">{geo_score}</span>
                    <span style="font-size: 14px; color: {color};">/100</span>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">GEO Score</p>
                </div>
            </div>
            """
        
        # GST row for Indian payments
        gst_row = ""
        if gst_display:
            gst_row = f"""
            <tr>
                <td style="padding: 8px 0; color: #666; font-size: 13px;">GST (18% incl.)</td>
                <td style="padding: 8px 0; text-align: right; color: #666; font-size: 13px;">{gst_display}</td>
            </tr>
            """
        
        content = f"""
        <h2 style="color: #1a1a1a; margin: 0 0 10px 0; font-size: 24px;">Payment Confirmed ✓</h2>
        <p style="color: #666; margin: 0 0 30px 0; font-size: 15px;">Your CiteKit package for <strong>{domain}</strong> is ready!</p>
        
        {score_badge}
        
        <!-- Invoice Box -->
        <div style="background: #fafafa; border: 1px solid #eee; border-radius: 12px; padding: 25px; margin: 25px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <div>
                    <p style="margin: 0; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Invoice</p>
                    <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: 600; color: #1a1a1a;">{invoice_number}</p>
                </div>
                <div style="text-align: right;">
                    <p style="margin: 0; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Date</p>
                    <p style="margin: 5px 0 0 0; font-size: 14px; color: #1a1a1a;">{invoice_date.strftime('%B %d, %Y')}</p>
                </div>
            </div>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
            
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #1a1a1a; font-size: 14px;">CiteKit AI Discoverability Package</td>
                    <td style="padding: 8px 0; text-align: right; color: #1a1a1a; font-size: 14px;">{base_display}</td>
                </tr>
                {gst_row}
            </table>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
            
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #1a1a1a; font-size: 16px; font-weight: 700;">Total Paid</td>
                    <td style="padding: 8px 0; text-align: right; color: #1a1a1a; font-size: 16px; font-weight: 700;">{amount_display}</td>
                </tr>
            </table>
            
            <p style="margin: 20px 0 0 0; font-size: 11px; color: #888; text-align: center;">
                Payment ID: {payment_id or 'N/A'}<br>
                Paid to: <strong>Jayso Labs Private Limited</strong>
            </p>
        </div>
        
        <!-- What's Included -->
        <h3 style="color: #1a1a1a; font-size: 16px; margin: 30px 0 15px 0;">📦 What's in your package:</h3>
        <ul style="color: #444; font-size: 14px; padding-left: 20px; margin: 0 0 25px 0;">
            <li style="margin-bottom: 8px;"><strong>llms.txt</strong> – AI-optimized content summary</li>
            <li style="margin-bottom: 8px;"><strong>mcp.json</strong> – Model Context Protocol configuration</li>
            <li style="margin-bottom: 8px;"><strong>facts.jsonld</strong> – Schema.org structured data</li>
            <li style="margin-bottom: 8px;"><strong>robots.txt</strong> – AI crawler directives</li>
            <li style="margin-bottom: 8px;"><strong>Audit Report</strong> – Detailed SEO analysis</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{download_url}" 
               style="display: inline-block; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);">
                ⬇️ Download Package
            </a>
        </div>
        
        <h3 style="color: #1a1a1a; font-size: 16px; margin: 30px 0 15px 0;">🚀 Next Steps:</h3>
        <ol style="color: #444; font-size: 14px; padding-left: 20px; margin: 0;">
            <li style="margin-bottom: 8px;">Download and extract the ZIP file</li>
            <li style="margin-bottom: 8px;">Upload files to your website's root directory</li>
            <li style="margin-bottom: 8px;">Verify by visiting: <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 4px;">{domain}/llms.txt</code></li>
        </ol>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="color: #666; font-size: 13px; text-align: center;">
            Questions? Reply to this email or contact us at <a href="mailto:hello@wantaiseo.com" style="color: #1a1a1a;">hello@wantaiseo.com</a>
        </p>
        """
        
        html_content = self._get_email_wrapper(content, show_unsubscribe=False, email=to_email)
        
        text_content = f"""
PAYMENT CONFIRMED

Your CiteKit package for {domain} is ready!

---
INVOICE: {invoice_number}
DATE: {invoice_date.strftime('%B %d, %Y')}
TOTAL: {amount_display}
PAYMENT ID: {payment_id or 'N/A'}
PAID TO: Jayso Labs Private Limited
---

WHAT'S INCLUDED:
- llms.txt – AI-optimized content summary
- mcp.json – Model Context Protocol configuration
- facts.jsonld – Schema.org structured data
- robots.txt – AI crawler directives
- Audit Report – Detailed SEO analysis

DOWNLOAD YOUR PACKAGE:
{download_url}

NEXT STEPS:
1. Download and extract the ZIP file
2. Upload files to your website's root directory
3. Verify by visiting: {domain}/llms.txt

Questions? Reply to this email or contact hello@wantaiseo.com

---
Reference: {job_id}
        """
        
        return self.send_email(
            to_email=to_email,
            subject=f"Your CiteKit Package for {domain} is Ready ✓",
            html_content=html_content,
            text_content=text_content,
            tags=["payment", "invoice", "download"]
        )

    def send_download_ready_email(
        self,
        to_email: str,
        domain: str,
        download_url: str,
        job_id: str
    ) -> bool:
        """Send just the download link (for users who already paid)"""
        
        content = f"""
        <h2 style="color: #1a1a1a; margin: 0 0 20px 0; font-size: 24px;">Your package is ready! 📦</h2>
        
        <p style="color: #444; font-size: 16px; margin-bottom: 25px;">
            Great news! Your CiteKit package for <strong>{domain}</strong> has been generated and is ready for download.
        </p>
        
        <div style="text-align: center; margin: 35px 0;">
            <a href="{download_url}" 
               style="display: inline-block; background: #1a1a1a; color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 16px;">
                ⬇️ Download Package
            </a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            This link will remain active. You can also access your package anytime from your <a href="{self.frontend_url}/dashboard" style="color: #1a1a1a;">dashboard</a>.
        </p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="font-size: 12px; color: #888;">Reference: {job_id}</p>
        """
        
        html_content = self._get_email_wrapper(content, show_unsubscribe=False, email=to_email)
        
        return self.send_email(
            to_email=to_email,
            subject=f"Your CiteKit Package for {domain} is Ready",
            html_content=html_content,
            tags=["download"]
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
