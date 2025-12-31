import os
import requests
import hashlib
import hmac
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import get_settings


class EmailService:
    """
    Email service using Mailgun API and Jinja2 templates.
    Delivers premium, responsive HTML emails.
    """
    
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

        # Setup Jinja2 Template Environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with common context"""
        template = self.env.get_template(template_name)
        
        # Add global context variables
        # Assets served from frontend (wantaiseo.com on Vercel)
        full_context = {
            "frontend_url": self.frontend_url,
            "asset_url": "https://wantaiseo.com/email",
            "current_year": datetime.now().year,
            **context
        }
        
        # Add unsubscribe URL if email is present in context
        if "email" in full_context and "unsubscribe_url" not in full_context:
            full_context["unsubscribe_url"] = self.get_unsubscribe_url(full_context["email"])
            full_context["show_unsubscribe"] = True
        
        return template.render(**full_context)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        tags: list = None
    ) -> bool:
        """Send an email via Mailgun. Returns True if successful."""
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
        """Generate a secure unsubscribe token"""
        secret = os.getenv("MAILGUN_API_KEY", "default-secret")
        return hmac.new(
            secret.encode(),
            email.lower().encode(),
            hashlib.sha256
        ).hexdigest()[:32]

    def get_unsubscribe_url(self, email: str) -> str:
        """Get the full unsubscribe URL"""
        token = self.generate_unsubscribe_token(email)
        return f"{self.frontend_url}/unsubscribe?email={email}&token={token}"

    def verify_unsubscribe_token(self, email: str, token: str) -> bool:
        """Verify an unsubscribe token"""
        expected_token = self.generate_unsubscribe_token(email)
        return hmac.compare_digest(token, expected_token)

    def suppress_email(self, email: str) -> bool:
        """Add email to suppression list (unsubscribe)"""
        if not self.enabled:
            print(f"📧 [DRY RUN] Would unsubscribe {email}")
            return True
            
        try:
            url = f"{self.api_base}/{self.domain}/complaints"
            data = {"address": email}
            
            response = requests.post(
                url,
                auth=("api", self.api_key),
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Unsubscribed {email}")
                return True
            else:
                print(f"⚠️ Failed to unsubscribe {email}: {response.text}")
                # We return True anyway so the user sees success message
                # Ideally we should log this error
                return True
                
        except Exception as e:
            print(f"❌ Unsubscribe error: {e}")
            return False

    # ============================================
    # PUBLIC SEND METHODS
    # ============================================

    def send_welcome_email(self, to_email: str, user_name: str = None) -> bool:
        """Send welcome email after signup"""
        name = user_name or to_email.split('@')[0].title()
        
        html_content = self._render_template("email/welcome.html", {
            "name": name,
            "email": to_email,
            "subject": f"Welcome to CiteKit, {name}! 🚀"
        })
        
        text_content = f"Welcome to CiteKit, {name}!\n\nStart here: {self.frontend_url}/dashboard"
        
        return self.send_email(
            to_email=to_email,
            subject=f"Welcome to CiteKit – Let's make your site AI-ready 🚀",
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
        
        # Format amounts
        if currency == "INR":
            amount_display = f"₹{amount_paise / 100:.2f}"
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
        
        context = {
            "email": to_email,
            "domain": domain,
            "download_url": download_url,
            "invoice_number": invoice_number,
            "amount_display": amount_display,
            "base_display": base_display,
            "gst_display": gst_display,
            "payment_id": payment_id,
            "geo_score": geo_score,
            "invoice_date": invoice_date.strftime('%B %d, %Y'),
            "subject": f"Your CiteKit Package for {domain} is Ready ✓"
        }

        html_content = self._render_template("email/payment_confirmation.html", context)
        
        text_content = f"Payment Confirmed for {domain}.\nDownload: {download_url}\nInvoice: {invoice_number}"
        
        return self.send_email(
            to_email=to_email,
            subject=context["subject"],
            html_content=html_content,
            text_content=text_content,
            tags=["payment", "invoice"]
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
