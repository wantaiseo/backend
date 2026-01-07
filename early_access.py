"""
Early Access Program

Self-serve trial code generation with testimonial commitment.
Users request free access in exchange for agreeing to provide a testimonial.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from auth import get_current_user
from database import get_database
from config import get_settings
from trial_codes import generate_code, TrialCodeType

router = APIRouter(prefix="/early-access", tags=["Early Access"])


# ============================================
# MODELS
# ============================================

class EarlyAccessRequest(BaseModel):
    """Request to join Early Access program"""
    job_id: str
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    role: Optional[str] = None  # e.g., "CEO", "Marketing Manager"
    company: Optional[str] = None
    website_url: Optional[str] = None  # The website they audited


class EarlyAccessResponse(BaseModel):
    """Response after joining Early Access"""
    success: bool
    message: str
    code: Optional[str] = None
    already_unlocked: bool = False


class EarlyAccessStats(BaseModel):
    """Stats for admin dashboard"""
    total_requests: int
    codes_generated: int
    testimonials_received: int
    slots_remaining: int


# ============================================
# CONFIGURATION
# ============================================

# Maximum early access slots (for scarcity)
MAX_EARLY_ACCESS_SLOTS = 100

# Days before follow-up email
FOLLOWUP_DAYS = 7


# ============================================
# ENDPOINTS
# ============================================

@router.post("/request", response_model=EarlyAccessResponse)
async def request_early_access(
    request: EarlyAccessRequest,
    user: dict = Depends(get_current_user)
):
    """
    Request Early Access - get a free trial code in exchange for
    agreeing to provide a testimonial.
    """
    db = get_database()
    settings = get_settings()
    
    user_id = user.get("id")
    user_email = user.get("email")
    
    # 1. Check if job exists and belongs to user
    job = await db.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 2. Check if job is already paid/unlocked
    if job.payment_id:
        return EarlyAccessResponse(
            success=True,
            message="This audit is already unlocked!",
            already_unlocked=True
        )
    
    # 3. Check if user already has an early access code (ONE PER LIFETIME)
    try:
        existing = db.client.table("early_access_requests").select("*").eq("user_id", user_id).execute()
        if existing.data and len(existing.data) > 0:
            existing_record = existing.data[0]
            existing_code = existing_record.get("trial_code")
            existing_job_id = existing_record.get("job_id")
            
            # Check if this is the SAME job they originally used trial for
            if request.job_id == existing_job_id:
                # Same job - it should already be unlocked
                return EarlyAccessResponse(
                    success=True,
                    message="This audit is already unlocked with your Early Access code!",
                    code=existing_code,
                    already_unlocked=True
                )
            else:
                # DIFFERENT job - user already used their one free trial
                # They need to pay for additional audits
                raise HTTPException(
                    status_code=400,
                    detail="You've already used your one-time free Early Access trial. Please purchase to unlock this audit."
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking existing early access: {e}")
    
    # 4. Check if slots are available
    try:
        count_result = db.client.table("early_access_requests").select("id", count="exact").execute()
        current_count = count_result.count or 0
        
        if current_count >= MAX_EARLY_ACCESS_SLOTS:
            raise HTTPException(
                status_code=400, 
                detail=f"Sorry, all {MAX_EARLY_ACCESS_SLOTS} Early Access slots are taken! Stay tuned for future promotions."
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking slot count: {e}")
        # Continue anyway if we can't check
    
    # 5. Generate unique trial code
    trial_code = generate_code(prefix="EARLY", length=8)
    
    # 6. Save to trial_codes table (Use Service Client to bypass RLS)
    try:
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        # Use service client for admin operations
        service_db = db.get_service_client()
        
        service_db.table("trial_codes").insert({
            "code": trial_code,
            "code_type": TrialCodeType.SINGLE_USE.value,
            "max_uses": 1,
            "current_uses": 0,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "created_by": "early_access_program",
            "note": f"Early Access for {user_email}",
            "is_active": True
        }).execute()
    except Exception as e:
        print(f"Error creating trial code: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate code")
    
    # 7. Save to early_access_requests table (Use Service Client)
    try:
        service_db.table("early_access_requests").insert({
            "user_id": user_id,
            "user_email": user_email,
            "trial_code": trial_code,
            "job_id": request.job_id,
            "linkedin_url": request.linkedin_url,
            "twitter_url": request.twitter_url,
            "role": request.role,
            "company": request.company,
            "website_url": request.website_url or job.url,
            "created_at": datetime.utcnow().isoformat(),
            "testimonial_status": "pending",  # pending, reminder_sent, received
            "followup_at": (datetime.utcnow() + timedelta(days=FOLLOWUP_DAYS)).isoformat()
        }).execute()
    except Exception as e:
        print(f"Error saving early access request: {e}")
        # Continue anyway - the trial code was created
    
    # 8. Apply code to the job immediately
    await db.update_job(request.job_id, payment_id=f"TRIAL:{trial_code}")
    
    # 9. Increment usage on trial code
    try:
        db.client.table("trial_codes").update({
            "current_uses": 1
        }).eq("code", trial_code).execute()
    except:
        pass
    
    # 10. Send confirmation email
    try:
        await send_early_access_email(
            email=user_email,
            code=trial_code,
            website=request.website_url or job.url
        )
    except Exception as e:
        print(f"Error sending early access email: {e}")
        # Non-critical, continue
    
    slots_remaining = MAX_EARLY_ACCESS_SLOTS - (current_count + 1) if 'current_count' in dir() else "?"
    
    return EarlyAccessResponse(
        success=True,
        message=f"🎉 Welcome to Early Access! Your download is now unlocked. ({slots_remaining} slots remaining)",
        code=trial_code
    )


@router.get("/status")
async def get_early_access_status(user: dict = Depends(get_current_user)):
    """Check if user already has Early Access"""
    db = get_database()
    user_id = user.get("id")
    
    try:
        existing = db.client.table("early_access_requests").select("*").eq("user_id", user_id).execute()
        
        if existing.data and len(existing.data) > 0:
            record = existing.data[0]
            return {
                "has_early_access": True,
                "already_used": True,  # User has already used their one-time trial
                "code": record.get("trial_code"),
                "used_for_job_id": record.get("job_id"),
                "used_for_website": record.get("website_url"),
                "created_at": record.get("created_at")
            }
    except Exception as e:
        print(f"Error checking early access status: {e}")
    
    return {"has_early_access": False, "already_used": False}


@router.get("/slots-remaining")
async def get_slots_remaining():
    """Public endpoint to show remaining slots (for urgency)"""
    db = get_database()
    
    try:
        count_result = db.client.table("early_access_requests").select("id", count="exact").execute()
        current_count = count_result.count or 0
        remaining = max(0, MAX_EARLY_ACCESS_SLOTS - current_count)
        
        return {
            "total_slots": MAX_EARLY_ACCESS_SLOTS,
            "used_slots": current_count,
            "remaining_slots": remaining,
            "is_available": remaining > 0
        }
    except Exception as e:
        print(f"Error getting slots: {e}")
        return {
            "total_slots": MAX_EARLY_ACCESS_SLOTS,
            "remaining_slots": MAX_EARLY_ACCESS_SLOTS,  # Assume available if error
            "is_available": True
        }


# ============================================
# EMAIL HELPER
# ============================================

async def send_early_access_email(email: str, code: str, website: str):
    """Send Early Access confirmation email"""
    from email_service import send_email
    
    subject = "🎉 Welcome to CiteKit Early Access!"
    
    html_content = f"""
    <div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #111; margin: 0;">🎉 You're In!</h1>
            <p style="color: #666; margin-top: 10px;">Welcome to the CiteKit Early Access Program</p>
        </div>
        
        <div style="background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%); color: white; padding: 30px; border-radius: 16px; text-align: center; margin-bottom: 30px;">
            <p style="margin: 0 0 10px; opacity: 0.9; font-size: 14px;">Your Early Access Code</p>
            <div style="font-size: 28px; font-weight: bold; font-family: monospace; letter-spacing: 2px;">{code}</div>
        </div>
        
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; padding: 20px; border-radius: 12px; margin-bottom: 30px;">
            <h3 style="color: #166534; margin: 0 0 10px;">✅ Your download is unlocked!</h3>
            <p style="color: #166534; margin: 0; font-size: 14px;">
                Go back to your audit results and click "Download" to get your AI Discoverability Kit for <strong>{website}</strong>.
            </p>
        </div>
        
        <div style="background: #FEF3C7; border: 1px solid #FCD34D; padding: 20px; border-radius: 12px; margin-bottom: 30px;">
            <h3 style="color: #92400E; margin: 0 0 10px;">📝 Your Promise</h3>
            <p style="color: #92400E; margin: 0; font-size: 14px;">
                As an Early Access member, you agreed to share a short testimonial after using CiteKit. 
                We'll send a friendly reminder in 7 days!
            </p>
        </div>
        
        <div style="border-top: 1px solid #eee; padding-top: 20px; text-align: center;">
            <p style="color: #999; font-size: 12px; margin: 0;">
                CiteKit - Make Your Website Visible to AI<br>
                <a href="https://wantaiseo.com" style="color: #3B82F6;">wantaiseo.com</a>
            </p>
        </div>
    </div>
    """
    
    await send_email(
        to_email=email,
        subject=subject,
        html_content=html_content
    )
