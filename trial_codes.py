"""
Trial Code System

Allows admins to generate promotional/trial codes that users can redeem
to unlock paid features without payment. Useful for:
- Getting early testimonials
- Beta testing
- Promotional campaigns
- Influencer partnerships
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class TrialCodeType(str, Enum):
    SINGLE_USE = "single_use"      # One-time use, expires after redeem
    MULTI_USE = "multi_use"        # Can be used by multiple users (up to max_uses)
    UNLIMITED = "unlimited"         # Unlimited uses (for major promos)


class TrialCode(BaseModel):
    """Trial code model"""
    code: str
    code_type: TrialCodeType = TrialCodeType.SINGLE_USE
    max_uses: int = 1              # Maximum number of redemptions
    current_uses: int = 0          # Current redemption count
    created_at: str                # ISO timestamp
    expires_at: Optional[str] = None  # ISO timestamp, None = never expires
    created_by: Optional[str] = None  # Admin who created it
    note: Optional[str] = None     # Internal note (e.g., "for influencer X")
    is_active: bool = True         # Can be deactivated by admin


class TrialCodeRedemption(BaseModel):
    """Record of a code redemption"""
    code: str
    user_id: str
    job_id: str
    redeemed_at: str               # ISO timestamp
    user_email: Optional[str] = None


class RedeemRequest(BaseModel):
    """Request to redeem a trial code"""
    code: str
    job_id: str


class RedeemResponse(BaseModel):
    """Response from redeeming a trial code"""
    success: bool
    message: str
    code: Optional[str] = None


class GenerateCodeRequest(BaseModel):
    """Admin request to generate trial codes"""
    count: int = 1                  # Number of codes to generate
    code_type: TrialCodeType = TrialCodeType.SINGLE_USE
    max_uses: int = 1               # For multi-use codes
    expires_in_days: Optional[int] = 30  # Days until expiry, None = never
    prefix: str = "CITE"            # Code prefix for branding
    note: Optional[str] = None      # Internal note


def generate_code(prefix: str = "CITE", length: int = 8) -> str:
    """
    Generate a unique, human-readable trial code.
    Format: PREFIX-XXXX-XXXX (e.g., CITE-AB12-CD34)
    """
    # Use only uppercase letters and numbers that aren't confusing (no O, 0, I, 1, L)
    safe_chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    
    # Generate random characters
    code_part = ''.join(secrets.choice(safe_chars) for _ in range(length))
    
    # Format as PREFIX-XXXX-XXXX
    code = f"{prefix.upper()}-{code_part[:4]}-{code_part[4:]}"
    
    return code


def generate_codes_batch(
    count: int = 1,
    code_type: TrialCodeType = TrialCodeType.SINGLE_USE,
    max_uses: int = 1,
    expires_in_days: Optional[int] = 30,
    prefix: str = "CITE",
    note: Optional[str] = None,
    created_by: Optional[str] = None
) -> List[TrialCode]:
    """
    Generate a batch of trial codes.
    
    Returns a list of TrialCode objects ready to be saved to database.
    """
    codes = []
    now = datetime.utcnow()
    expires_at = None
    
    if expires_in_days:
        expires_at = (now + timedelta(days=expires_in_days)).isoformat()
    
    for _ in range(count):
        code = generate_code(prefix=prefix)
        
        trial_code = TrialCode(
            code=code,
            code_type=code_type,
            max_uses=max_uses,
            current_uses=0,
            created_at=now.isoformat(),
            expires_at=expires_at,
            created_by=created_by,
            note=note,
            is_active=True
        )
        codes.append(trial_code)
    
    return codes


def is_code_valid(code: TrialCode) -> tuple[bool, str]:
    """
    Check if a trial code is valid for redemption.
    
    Returns: (is_valid, reason)
    """
    # Check if active
    if not code.is_active:
        return False, "This code has been deactivated."
    
    # Check expiration
    if code.expires_at:
        expires = datetime.fromisoformat(code.expires_at.replace('Z', '+00:00'))
        if datetime.utcnow() > expires:
            return False, "This code has expired."
    
    # Check usage limit
    if code.code_type != TrialCodeType.UNLIMITED:
        if code.current_uses >= code.max_uses:
            return False, "This code has already been used."
    
    return True, "Code is valid."


# ============================================
# DATABASE OPERATIONS (Supabase)
# ============================================

async def create_trial_code_table_if_not_exists(db):
    """
    Create the trial_codes table if it doesn't exist.
    This should be run once during setup.
    
    SQL for manual creation:
    
    CREATE TABLE IF NOT EXISTS trial_codes (
        code TEXT PRIMARY KEY,
        code_type TEXT NOT NULL DEFAULT 'single_use',
        max_uses INTEGER NOT NULL DEFAULT 1,
        current_uses INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ,
        created_by TEXT,
        note TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    );
    
    CREATE TABLE IF NOT EXISTS trial_redemptions (
        id SERIAL PRIMARY KEY,
        code TEXT NOT NULL REFERENCES trial_codes(code),
        user_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        user_email TEXT,
        UNIQUE(code, user_id, job_id)
    );
    
    CREATE INDEX idx_trial_codes_active ON trial_codes(is_active) WHERE is_active = TRUE;
    CREATE INDEX idx_trial_redemptions_user ON trial_redemptions(user_id);
    """
    pass  # Table creation should be done via Supabase dashboard or migration


async def save_trial_codes(db, codes: List[TrialCode]) -> bool:
    """Save generated trial codes to database."""
    try:
        for code in codes:
            await db.supabase.table("trial_codes").insert(code.model_dump()).execute()
        return True
    except Exception as e:
        print(f"Error saving trial codes: {e}")
        return False


async def get_trial_code(db, code: str) -> Optional[TrialCode]:
    """Get a trial code from database."""
    try:
        result = await db.supabase.table("trial_codes").select("*").eq("code", code.upper()).single().execute()
        if result.data:
            return TrialCode(**result.data)
        return None
    except Exception:
        return None


async def redeem_trial_code(
    db,
    code: str,
    user_id: str,
    job_id: str,
    user_email: Optional[str] = None
) -> tuple[bool, str]:
    """
    Attempt to redeem a trial code for a job.
    
    Returns: (success, message)
    """
    code = code.upper().strip()
    
    # Get the code
    trial_code = await get_trial_code(db, code)
    
    if not trial_code:
        return False, "Invalid code. Please check and try again."
    
    # Validate the code
    is_valid, reason = is_code_valid(trial_code)
    if not is_valid:
        return False, reason
    
    # Check if user already redeemed this code for this job
    try:
        existing = await db.supabase.table("trial_redemptions").select("*").eq("code", code).eq("user_id", user_id).eq("job_id", job_id).execute()
        if existing.data and len(existing.data) > 0:
            return False, "You've already used this code for this audit."
    except Exception:
        pass  # Continue if check fails
    
    try:
        # Record the redemption
        redemption = {
            "code": code,
            "user_id": user_id,
            "job_id": job_id,
            "redeemed_at": datetime.utcnow().isoformat(),
            "user_email": user_email
        }
        await db.supabase.table("trial_redemptions").insert(redemption).execute()
        
        # Increment usage count
        await db.supabase.table("trial_codes").update({
            "current_uses": trial_code.current_uses + 1
        }).eq("code", code).execute()
        
        # Mark the job as "paid" (unlocked via trial code)
        await db.update_job(job_id, payment_id=f"TRIAL:{code}")
        
        return True, "Code redeemed successfully! Your download is now unlocked."
        
    except Exception as e:
        print(f"Error redeeming trial code: {e}")
        return False, "Something went wrong. Please try again."


async def get_all_trial_codes(db, include_inactive: bool = False) -> List[dict]:
    """Get all trial codes for admin view."""
    try:
        query = db.supabase.table("trial_codes").select("*").order("created_at", desc=True)
        if not include_inactive:
            query = query.eq("is_active", True)
        result = await query.execute()
        return result.data or []
    except Exception as e:
        print(f"Error fetching trial codes: {e}")
        return []


async def deactivate_trial_code(db, code: str) -> bool:
    """Deactivate a trial code."""
    try:
        await db.supabase.table("trial_codes").update({
            "is_active": False
        }).eq("code", code.upper()).execute()
        return True
    except Exception:
        return False
