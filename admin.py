"""
CiteKit – Admin API
Protected endpoints for admin dashboard
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import logging

from auth import get_current_user
from database import Database
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/admin", tags=["admin"])

# ============================================
# MODELS
# ============================================

class AdminStats(BaseModel):
    total_users: int = 0
    new_users_today: int = 0
    new_users_week: int = 0
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    pending_jobs: int = 0
    success_rate: float = 0.0
    total_revenue: float = 0.0
    revenue_today: float = 0.0
    revenue_week: float = 0.0
    revenue_month: float = 0.0

class UserInfo(BaseModel):
    id: str
    email: str
    created_at: str
    jobs_count: int = 0
    total_spent: float = 0.0

class JobInfo(BaseModel):
    id: str
    user_email: str
    url: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    pages_crawled: int = 0
    error: Optional[str] = None

class PaymentInfo(BaseModel):
    id: str
    user_email: str
    amount: float
    status: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    created_at: str

# ============================================
# ADMIN CHECK DEPENDENCY
# ============================================

# Hardcoded admin email for simplicity (single admin)
# In production, check against admins table
ADMIN_EMAILS = [
    settings.admin_email,
    "samaypatel0402@gmail.com",  # Backup
]

async def require_admin(user: dict = Depends(get_current_user)):
    """Check if current user is an admin"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_email = user.get("email", "")
    
    # Check hardcoded admin list first
    if user_email in ADMIN_EMAILS:
        return user
    
    # Check database admins table
    try:
        db = Database()
        if db.client:
            result = db.client.table("admins").select("*").eq("user_id", user.get("id")).execute()
            if result.data and len(result.data) > 0:
                return user
    except Exception as e:
        logger.warning(f"Failed to check admin status in DB: {e}")
    
    raise HTTPException(status_code=403, detail="Admin access required")

# ============================================
# DASHBOARD STATS
# ============================================

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(admin: dict = Depends(require_admin)):
    """Get overview statistics for admin dashboard"""
    db = Database()
    stats = AdminStats()
    
    try:
        if db.client:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Total users
            try:
                users_result = db.client.rpc('get_user_count').execute()
                if users_result.data:
                    stats.total_users = users_result.data or 0
            except Exception as e:
                logger.warning(f"Failed to get user count via RPC: {e}")
            
            # Jobs stats
            jobs_result = db.client.table("jobs").select("job_id, status, created_at").execute()
            if jobs_result.data:
                all_jobs = jobs_result.data
                stats.total_jobs = len(all_jobs)
                stats.completed_jobs = len([j for j in all_jobs if j.get("status") == "completed"])
                stats.failed_jobs = len([j for j in all_jobs if j.get("status") == "failed"])
                stats.pending_jobs = len([j for j in all_jobs if j.get("status") in ["pending", "discovering", "crawling", "extracting", "classifying", "synthesizing", "packaging"]])
                
                if stats.total_jobs > 0:
                    stats.success_rate = round((stats.completed_jobs / stats.total_jobs) * 100, 1)
            
            # Revenue stats
            payments_result = db.client.table("payment_orders").select("amount, status, created_at").eq("status", "completed").execute()
            if payments_result.data:
                all_payments = payments_result.data
                # Convert paise to INR for all stats
                stats.total_revenue = sum(p.get("amount", 0) for p in all_payments) / 100.0
                
                # Today's revenue
                stats.revenue_today = sum(
                    p.get("amount", 0) for p in all_payments 
                    if p.get("created_at", "")[:10] == today_start.strftime("%Y-%m-%d")
                ) / 100.0
                
                # Week revenue
                stats.revenue_week = sum(
                    p.get("amount", 0) for p in all_payments
                    if p.get("created_at", "") >= week_ago.isoformat()
                ) / 100.0
                
                # Month revenue
                stats.revenue_month = sum(
                    p.get("amount", 0) for p in all_payments
                    if p.get("created_at", "") >= month_ago.isoformat()
                ) / 100.0
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get admin stats: {e}")
        return stats

# ============================================
# USERS MANAGEMENT
# ============================================

@router.get("/users")
async def get_all_users(
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(require_admin)
):
    """Get list of all users"""
    db = Database()
    
    try:
        if db.client:
            # Get jobs grouped by user
            jobs_result = db.client.table("jobs").select("user_id, job_id").execute()
            jobs_by_user = {}
            if jobs_result.data:
                for job in jobs_result.data:
                    uid = job.get("user_id")
                    if uid:
                        jobs_by_user[uid] = jobs_by_user.get(uid, 0) + 1
            
            # Get payments by user
            payments_result = db.client.table("payment_orders").select("user_id, amount").eq("status", "completed").execute()
            payments_by_user = {}
            if payments_result.data:
                for payment in payments_result.data:
                    uid = payment.get("user_id")
                    if uid:
                        payments_by_user[uid] = payments_by_user.get(uid, 0) + payment.get("amount", 0)
            
            # Get users from auth.users via RPC or direct query
            # Note: This requires a custom RPC function in Supabase
            users = []
            try:
                users_result = db.client.rpc('get_all_users', {"limit_count": limit, "offset_count": offset}).execute()
                if users_result.data:
                    for u in users_result.data:
                        uid = u.get("id")
                        users.append({
                            "id": uid,
                            "email": u.get("email"),
                            "created_at": u.get("created_at"),
                            "jobs_count": jobs_by_user.get(uid, 0),
                            "total_spent": payments_by_user.get(uid, 0) / 100.0
                        })
            except Exception as rpc_error:
                logger.warning(f"RPC get_all_users failed: {rpc_error}")
            
            return {"users": users, "total": len(users)}
        
        return {"users": [], "total": 0}
        
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        return {"users": [], "total": 0, "error": str(e)}

# ============================================
# JOBS MANAGEMENT
# ============================================

@router.get("/jobs")
async def get_all_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(require_admin)
):
    """Get list of all jobs with optional status filter"""
    db = Database()
    
    try:
        if db.client:
            query = db.client.table("jobs").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
            
            if status:
                query = query.eq("status", status)
            
            result = query.execute()
            
            jobs = []
            if result.data:
                for j in result.data:
                    jobs.append({
                        "id": j.get("job_id"),
                        "user_id": j.get("user_id"),
                        "url": j.get("url"),
                        "status": j.get("status"),
                        "created_at": j.get("created_at"),
                        "completed_at": j.get("completed_at"),
                        "pages_count": j.get("pages_count", 0),
                        "error": j.get("error")
                    })
            
            return {"jobs": jobs, "total": len(jobs)}
        
        return {"jobs": [], "total": 0}
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        return {"jobs": [], "total": 0, "error": str(e)}

@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str, admin: dict = Depends(require_admin)):
    """Get detailed info about a specific job"""
    db = Database()
    job = await db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, admin: dict = Depends(require_admin)):
    """Cancel a running job"""
    db = Database()
    
    try:
        if db.client:
            result = db.client.table("jobs").update({
                "status": "cancelled",
                "error": "Cancelled by admin"
            }).eq("job_id", job_id).execute()
            
            # Log admin action
            db.client.table("admin_activity_log").insert({
                "admin_user_id": admin.get("id"),
                "action": "cancel_job",
                "target_type": "job",
                "target_id": job_id
            }).execute()
            
            return {"success": True, "message": f"Job {job_id} cancelled"}
        
        return {"success": False, "message": "Database not available"}
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PAYMENTS
# ============================================

@router.get("/payments")
async def get_all_payments(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(require_admin)
):
    """Get list of all payments"""
    db = Database()
    
    try:
        if db.client:
            query = db.client.table("payment_orders").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
            
            if status:
                query = query.eq("status", status)
            
            result = query.execute()
            
            payments = []
            if result.data:
                for p in result.data:
                    payments.append({
                        "id": p.get("id"),
                        "user_id": p.get("user_id"),
                        "amount": p.get("amount", 0) / 100.0 if p.get("amount") else 0,
                        "currency": p.get("currency", "INR"),
                        "status": p.get("status"),
                        "razorpay_order_id": p.get("razorpay_order_id"),
                        "razorpay_payment_id": p.get("razorpay_payment_id"),
                        "job_id": p.get("job_id"),
                        "created_at": p.get("created_at")
                    })
            
            return {"payments": payments, "total": len(payments)}
        
        return {"payments": [], "total": 0}
        
    except Exception as e:
        logger.error(f"Failed to get payments: {e}")
        return {"payments": [], "total": 0, "error": str(e)}

# ============================================
# SYSTEM MONITORING
# ============================================

@router.get("/system/health")
async def get_system_health(admin: dict = Depends(require_admin)):
    """Get current system health status"""
    db = Database()
    
    health = {
        "api_status": "healthy",
        "database_status": "unknown",
        "celery_status": "unknown",
        "active_jobs": 0,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Check database
        if db.client:
            db.client.table("jobs").select("job_id").limit(1).execute()
            health["database_status"] = "healthy"
        
        # Count active jobs
        if db.client:
            active_result = db.client.table("jobs").select("job_id").in_(
                "status", 
                ["pending", "discovering", "crawling", "extracting", "classifying", "synthesizing", "packaging"]
            ).execute()
            health["active_jobs"] = len(active_result.data) if active_result.data else 0
        
        # Try to check Celery (basic ping)
        try:
            from celery_app import celery_app
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            if stats:
                health["celery_status"] = "healthy"
                health["celery_workers"] = len(stats)
            else:
                health["celery_status"] = "no_workers"
        except Exception as e:
            health["celery_status"] = f"error: {str(e)[:50]}"
        
        return health
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health["database_status"] = f"error: {str(e)[:50]}"
        return health

@router.get("/system/recent-errors")
async def get_recent_errors(
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """Get recent failed jobs and errors"""
    db = Database()
    
    try:
        if db.client:
            result = db.client.table("jobs").select("job_id, url, status, error, created_at").eq("status", "failed").order("created_at", desc=True).limit(limit).execute()
            
            return {"errors": result.data or []}
        
        return {"errors": []}
        
    except Exception as e:
        logger.error(f"Failed to get errors: {e}")
        return {"errors": [], "error": str(e)}

# ============================================
# ACTIVITY LOG
# ============================================

@router.get("/activity-log")
async def get_activity_log(
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Get admin activity log"""
    db = Database()
    
    try:
        if db.client:
            result = db.client.table("admin_activity_log").select("*").order("created_at", desc=True).limit(limit).execute()
            
            return {"logs": result.data or []}
        
        return {"logs": []}
        
    except Exception as e:
        logger.error(f"Failed to get activity log: {e}")
        return {"logs": [], "error": str(e)}


# ============================================
# TRIAL CODES MANAGEMENT
# ============================================

class GenerateTrialCodesRequest(BaseModel):
    count: int = 1
    prefix: str = "CITE"
    expires_in_days: Optional[int] = 30
    note: Optional[str] = None
    max_uses: int = 1  # For multi-use codes


@router.post("/trial-codes/generate")
async def generate_trial_codes(
    request: GenerateTrialCodesRequest,
    admin: dict = Depends(require_admin)
):
    """Generate new trial codes for promotional purposes"""
    from trial_codes import generate_codes_batch, TrialCodeType
    
    db = Database()
    
    try:
        # Determine code type based on max_uses
        code_type = TrialCodeType.SINGLE_USE if request.max_uses == 1 else TrialCodeType.MULTI_USE
        
        # Generate codes
        codes = generate_codes_batch(
            count=min(request.count, 100),  # Cap at 100 per request
            code_type=code_type,
            max_uses=request.max_uses,
            expires_in_days=request.expires_in_days,
            prefix=request.prefix,
            note=request.note,
            created_by=admin.get("email")
        )
        
        # Save to database
        if db.client:
            for code in codes:
                db.client.table("trial_codes").insert(code.model_dump()).execute()
        
        # Log admin action
        if db.client:
            try:
                db.client.table("admin_activity_log").insert({
                    "admin_user_id": admin.get("id"),
                    "action": "generate_trial_codes",
                    "target_type": "trial_codes",
                    "details": f"Generated {len(codes)} codes with prefix {request.prefix}"
                }).execute()
            except:
                pass
        
        return {
            "success": True,
            "codes": [c.code for c in codes],
            "count": len(codes),
            "expires_at": codes[0].expires_at if codes else None
        }
        
    except Exception as e:
        logger.error(f"Failed to generate trial codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trial-codes")
async def get_all_trial_codes(
    include_inactive: bool = False,
    admin: dict = Depends(require_admin)
):
    """Get all trial codes with usage stats"""
    db = Database()
    
    try:
        if db.client:
            query = db.client.table("trial_codes").select("*").order("created_at", desc=True)
            if not include_inactive:
                query = query.eq("is_active", True)
            result = query.execute()
            
            # Get redemption counts
            redemptions_result = db.client.table("trial_redemptions").select("code, user_email, redeemed_at").execute()
            redemptions_by_code = {}
            if redemptions_result.data:
                for r in redemptions_result.data:
                    code = r.get("code")
                    if code not in redemptions_by_code:
                        redemptions_by_code[code] = []
                    redemptions_by_code[code].append({
                        "email": r.get("user_email"),
                        "redeemed_at": r.get("redeemed_at")
                    })
            
            codes = []
            if result.data:
                for c in result.data:
                    code = c.get("code")
                    codes.append({
                        **c,
                        "redemptions": redemptions_by_code.get(code, [])
                    })
            
            return {"codes": codes, "total": len(codes)}
        
        return {"codes": [], "total": 0}
        
    except Exception as e:
        logger.error(f"Failed to get trial codes: {e}")
        return {"codes": [], "total": 0, "error": str(e)}


@router.post("/trial-codes/{code}/deactivate")
async def deactivate_trial_code(
    code: str,
    admin: dict = Depends(require_admin)
):
    """Deactivate a trial code"""
    db = Database()
    
    try:
        if db.client:
            db.client.table("trial_codes").update({
                "is_active": False
            }).eq("code", code.upper()).execute()
            
            # Log admin action
            try:
                db.client.table("admin_activity_log").insert({
                    "admin_user_id": admin.get("id"),
                    "action": "deactivate_trial_code",
                    "target_type": "trial_code",
                    "target_id": code
                }).execute()
            except:
                pass
            
            return {"success": True, "message": f"Code {code} deactivated"}
        
        return {"success": False, "message": "Database not available"}
        
    except Exception as e:
        logger.error(f"Failed to deactivate trial code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trial-codes/stats")
async def get_trial_code_stats(
    admin: dict = Depends(require_admin)
):
    """Get trial code usage statistics"""
    db = Database()
    
    try:
        if db.client:
            # Get all codes
            codes_result = db.client.table("trial_codes").select("*").execute()
            codes = codes_result.data or []
            
            # Get all redemptions
            redemptions_result = db.client.table("trial_redemptions").select("*").execute()
            redemptions = redemptions_result.data or []
            
            active_codes = len([c for c in codes if c.get("is_active")])
            total_codes = len(codes)
            total_redemptions = len(redemptions)
            
            return {
                "total_codes": total_codes,
                "active_codes": active_codes,
                "inactive_codes": total_codes - active_codes,
                "total_redemptions": total_redemptions,
                "unique_users": len(set(r.get("user_id") for r in redemptions))
            }
        
        return {}
        
    except Exception as e:
        logger.error(f"Failed to get trial code stats: {e}")
        return {"error": str(e)}

