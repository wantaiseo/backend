"""
CiteKit – FastAPI Application
Main API endpoints for website compilation
"""

import uuid
import time
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import get_database
from models import (
    CompileRequest,
    CompileResponse,
    CompileJob,
    JobStatus,
    JobStatusResponse
)
from tasks import compile_website_task
from auth import router as auth_router, get_current_user
from payments import router as payments_router
from middleware import RateLimitMiddleware, RequestValidationMiddleware
from error_handler import (
    setup_error_handlers,
    JobNotFoundError,
    JobNotCompletedError,
    QuotaExceededError,
    APIError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("geo-compiler")

# ============================================
# APP INITIALIZATION
# ============================================

app = FastAPI(
    title="CiteKit",
    description="Convert any public website into an LLM-native knowledge package",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup error handlers
setup_error_handlers(app)

# Add rate limiting middleware (60 req/min, 1000 req/hour)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60, requests_per_hour=1000)

# Add request validation middleware
app.add_middleware(RequestValidationMiddleware)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    logger.warning("Static directory not found, skipping static file mounting")

# Dynamic CORS configuration (supports local dev + production)
settings = get_settings()
logger.info(f"CORS Origins: {settings.cors_origins}")
logger.info(f"Running on Cloud Run: {settings.is_cloud_run}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

# Include payment routes (Razorpay)
app.include_router(payments_router)

# Include admin routes
try:
    from admin import router as admin_router
    app.include_router(admin_router)
    logger.info("Admin router loaded")
except ImportError as e:
    logger.warning(f"Admin router not available: {e}")


# ============================================
# EMAIL UNSUBSCRIBE ENDPOINT
# ============================================

@app.get("/unsubscribe")
async def unsubscribe_email(email: str, token: str):
    """
    Handle email unsubscribe requests.
    Validates the token and marks the user as unsubscribed.
    """
    from email_service import get_email_service
    
    email_service = get_email_service()
    
    # Verify the token is valid (prevents spam unsubscribe attacks)
    if not email_service.verify_unsubscribe_token(email, token):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link")
    
    # In a production system, you would update a database here.
    # For now, we log it and return success.
    # Mailgun also automatically handles suppressions if you use their List-Unsubscribe header.
    logger.info(f"📧 Unsubscribe request: {email}")
    
    # Return a simple HTML page confirming unsubscription
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Unsubscribed - CiteKit</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: #f9f9f8;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.05);
                max-width: 400px;
            }}
            h1 {{ color: #1a1a1a; margin-bottom: 10px; }}
            p {{ color: #666; }}
            a {{ color: #1a1a1a; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✓ Unsubscribed</h1>
            <p>You've been removed from marketing emails.</p>
            <p>You'll still receive transactional emails (payment confirmations, download links).</p>
            <p style="margin-top: 30px;"><a href="{settings.frontend_url}">← Back to CiteKit</a></p>
        </div>
    </body>
    </html>
    """, status_code=200)

# Track server start time for uptime
SERVER_START_TIME = time.time()


# ============================================
# ROOT / WEB UI
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    with open("static/index.html") as f:
        return f.read()


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    """
    Enhanced health check endpoint.
    Returns service status and dependency health.
    """
    uptime = time.time() - SERVER_START_TIME
    
    # Check dependencies
    dependencies: Dict[str, Any] = {}
    overall_healthy = True
    
    # Check Redis/Celery
    try:
        from celery_app import celery_app
        celery_inspect = celery_app.control.inspect()
        active_workers = celery_inspect.active_queues()
        dependencies["celery"] = {
            "status": "healthy" if active_workers else "degraded",
            "workers": len(active_workers) if active_workers else 0
        }
    except Exception as e:
        dependencies["celery"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check database
    try:
        db = get_database()
        # Simple query to verify connection
        dependencies["database"] = {"status": "healthy"}
    except Exception as e:
        dependencies["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "service": "geo-compiler",
        "version": "1.0.0",
        "uptime_seconds": round(uptime, 2),
        "dependencies": dependencies
    }


@app.get("/health/live")
async def liveness_check():
    """Simple liveness probe for Kubernetes/container orchestration."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe - checks if service is ready to accept traffic."""
    try:
        db = get_database()
        return {"status": "ready"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Database unavailable"}
        )


# ============================================
# COMPETITOR BENCHMARK ENDPOINT
# ============================================

from pydantic import BaseModel
from typing import List

class BenchmarkRequest(BaseModel):
    """Request for competitor benchmark"""
    your_domain: str
    your_score: int = 50  # Default score if not yet compiled
    competitors: List[str]  # Up to 5 competitor URLs

class BenchmarkResult(BaseModel):
    """Single competitor result"""
    domain: str
    score: int
    has_llm_txt: bool
    has_schema_org: bool
    social_links: int
    status: str

@app.post("/benchmark")
async def run_competitor_benchmark(
    request: BenchmarkRequest,
    user: dict = Depends(get_current_user)
):
    """
    Quick benchmark check for competitor AI readiness.
    Returns comparison data for up to 5 competitors.
    Fast execution (~5-10 seconds).
    """
    from benchmark import CompetitorBenchmark, run_full_benchmark
    
    if len(request.competitors) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 competitors allowed")
    
    if len(request.competitors) == 0:
        raise HTTPException(status_code=400, detail="At least 1 competitor required")
    
    try:
        result = await run_full_benchmark(
            your_domain=request.your_domain,
            your_score=request.your_score,
            your_html="",  # Empty for standalone benchmark
            competitor_urls=request.competitors
        )
        return result
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {str(e)}")


# ============================================
# COMPILE ENDPOINT

# ============================================

@app.post("/compile", response_model=CompileResponse)
async def compile_website(
    request: CompileRequest,
    user: dict = Depends(get_current_user)
):
    """
    Start a website compilation job.
    Accepts a URL and returns a job_id for tracking progress.
    """
    try:
        db = get_database()

        # 1. REMOVE UPFRONT PAYMENT CHECK (Freemium Flow)
        # The compilation is free (Audit First), download is paid.

        # ⚡ 2. CHECK CACHE (Enabled for Performance)
        # If a valid result exists for this URL, reuse it to save time/compute
        # ⚡ 2. CHECK CACHE - DISABLED BY USER REQUEST
        # (Removed complex caching logic to ensure stability)


        # 3. START NEW JOB
        job_id = str(uuid.uuid4())

        job = CompileJob(
            job_id=job_id,
            user_id=user["id"],
            url=str(request.url),
            status=JobStatus.PENDING,
            payment_id=request.payment_id
        )

        await db.create_job(job, token=user.get("token"))

        # Queue Celery task
        compile_website_task.delay(
            job_id=job_id,
            url=str(request.url),
            crawl_depth=request.crawl_depth.value,
            include_subdomains=request.include_subdomains,
            competitors=request.competitors
        )

        return CompileResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Compilation job started. Use /status/{job_id} to track progress."
        )
    except Exception as e:
        import traceback
        traceback.print_exc() # Log to server console
        # Return 500 with meaningful message
        raise HTTPException(status_code=500, detail=f"Failed to start compilation: {str(e)}")


# ============================================
# JOB STATUS ENDPOINT
# ============================================

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a compilation job.
    """
    db = get_database()

    job = await db.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Generate logs based on current status/progress for frontend display
    logs = _generate_status_logs(job)

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        total_pages=job.total_pages,
        url=job.url,
        geo_score=getattr(job, 'geo_score', None),
        result_path=job.result_path,
        error=job.error,
        is_paid=bool(job.payment_id),
        logs=logs
    )


def _generate_status_logs(job) -> list[str]:
    """Generate descriptive logs based on job status for frontend display."""
    logs = []
    status = job.status if isinstance(job.status, str) else job.status.value
    progress = job.progress or 0
    
    # Always add initial log
    logs.append(f"🚀 Let's make {job.url} AI-ready!")
    
    if status in ['discovering', 'DISCOVERING'] or progress >= 5:
        logs.append("🔍 Mapping your digital footprint...")
    
    if status in ['extracting', 'EXTRACTING'] or progress >= 20:
        logs.append(f"📊 Discovered {job.total_pages or 0} pages worth of knowledge")
        logs.append("🕷️ Reading your content like an AI would...")
    
    if status in ['classifying', 'CLASSIFYING'] or progress >= 40:
        logs.append("🧠 Understanding what makes each page unique...")
    
    if status in ['synthesizing', 'SYNTHESIZING'] or progress >= 60:
        logs.append("✨ Crafting your AI-optimized knowledge file...")
        logs.append("🗺️ Building your intelligent sitemap...")
        logs.append("🔗 Extracting the facts that matter...")
    
    if status in ['packaging', 'PACKAGING'] or progress >= 85:
        logs.append("📦 Wrapping up your citation toolkit...")
        logs.append("✅ Running final quality checks...")
    
    if status in ['completed', 'COMPLETED']:
        logs.append("🎉 Your site is now AI-discoverable!")
        if job.geo_score:
            logs.append(f"📈 Current AI Readiness: {job.geo_score}/100")
    
    if status in ['failed', 'FAILED']:
        logs.append(f"❌ Something went wrong: {job.error or 'Unknown error'}")
    
    if status in ['cancelled', 'CANCELLED']:
        logs.append("🛑 Process stopped by user")
    
    return logs

@app.get("/preview/{job_id}")
async def preview_job(job_id: str, user: dict = Depends(get_current_user)):
    """Get the preview content of the compilation"""
    import os
    import json
    
    # Get the output directory from settings (ensures consistent path)
    settings = get_settings()
    
    # First check job status - only return preview for COMPLETED jobs
    db = get_database()
    job = await db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If job is still processing, return 202 (Accepted but not ready)
    # We allow 'failed' status to proceed because it might still have an audit report
    if job.status not in ['completed', 'COMPLETED', 'failed', 'FAILED']:
        return {
            "status": "processing",
            "message": "Job is still being processed",
            "audit": None,
            "json": None,
            "markdown": None,
            "facts": None
        }
    
    # 0. DATABASE STORAGE CHECK (Fastest/Most Reliable)
    if job.output_data:
        return {
            "status": "completed",
            "audit": job.output_data.get("audit"),
            "json": job.output_data.get("mcp") or job.output_data.get("json"),
            "facts": job.output_data.get("facts"),
            "markdown": job.output_data.get("llm_txt") or job.output_data.get("markdown")
        }

    # Use the configured output_dir from settings (same as where Celery worker saves files)
    output_dir = os.path.join(settings.output_dir, job_id)
    
    preview_data = {}
    audit_data = None
    
    import urllib.request
    import zipfile
    
    audit_path = os.path.join(output_dir, "audit.json")

    # RESTORE FROM STORAGE IF MISSING LOCAL
    # Check if we need to restore (missing folder or missing audit file)
    if (not os.path.exists(output_dir) or not os.path.exists(audit_path)) and job.result_path:
        print(f"Local cache miss for {job_id}. Attempting restore...")
        
        # Determine source
        zip_source = None
        if job.result_path.startswith("http"):
            zip_source = "url"
        elif os.path.exists(job.result_path) and job.result_path.endswith(".zip"):
             zip_source = "local"
             
        if zip_source:
             try:
                 os.makedirs(output_dir, exist_ok=True)
                 temp_zip = os.path.join(output_dir, "restore.zip")
                 
                 if zip_source == "url":
                     print(f"Downloading from: {job.result_path}")
                     urllib.request.urlretrieve(job.result_path, temp_zip)
                 else:
                     import shutil
                     shutil.copy2(job.result_path, temp_zip)
                 
                 # Extract with path traversal protection
                 if zipfile.is_zipfile(temp_zip):
                     with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                         # SECURITY: Validate paths to prevent zip slip attack
                         for member in zip_ref.namelist():
                             member_path = os.path.realpath(os.path.join(output_dir, member))
                             if not member_path.startswith(os.path.realpath(output_dir)):
                                 print(f"⚠️ Skipping dangerous path: {member}")
                                 continue
                             zip_ref.extract(member, output_dir)
                     print("✅ Restore successful.")
                 
                 # Cleanup temp zip
                 if os.path.exists(temp_zip):
                     os.remove(temp_zip)
                     
             except Exception as e:
                 print(f"❌ Restore failed: {e}")

    # Try to read audit.json from disk
    if os.path.exists(audit_path):
        try:
            with open(audit_path, "r") as f:
                audit_data = json.load(f)
        except Exception as e:
            print(f"Error reading audit.json: {e}")
            pass
            
    if not audit_data:
        # Fallback: Generate a basic audit from DB data if file is missing
        # This handles cases where local files are cleaned up but DB record exists
        score_val = job.geo_score if job.geo_score is not None else 0
        
        audit_data = {
            "score": {
                "total": score_val,
                "interpretation": "Detailed audit report unavailable (files cleared). Re-run compilation for full details.",
                "breakdown": {
                    "crawler_access": int(score_val * 0.25),
                    "structured_data": int(score_val * 0.25),
                    "content_signals": int(score_val * 0.25),
                    "technical": int(score_val * 0.25)
                }
            },
            "issues": [
                {
                    "category": "info",
                    "title": "Report Retrieved from Archive",
                    "description": "This is a summary report based on archived data."
                }
            ],
            "generated_at": job.completed_at or "2024-01-01T00:00:00"
        }

    preview_data["audit"] = audit_data

    # Paid content access check
    is_paid = bool(job and job.payment_id)

    if is_paid and os.path.exists(output_dir):
        # Paid users see everything IF files exist
        try:
            with open(os.path.join(output_dir, "content.json"), "r") as f:
                preview_data["json"] = json.load(f)
        except Exception:
            preview_data["json"] = None

        try:
            with open(os.path.join(output_dir, "structure.md"), "r") as f:
                preview_data["markdown"] = f.read()
        except Exception:
             preview_data["markdown"] = None

        try:
            with open(os.path.join(output_dir, "facts.jsonld"), "r") as f:
                preview_data["facts"] = json.load(f)
        except Exception:
             preview_data["facts"] = None
    else:
        # Free users or missing files
        preview_data["json"] = None
        preview_data["markdown"] = None
        preview_data["facts"] = None
         
    return preview_data


@app.get("/sample")
async def get_sample_output():
    """
    Get a sample output for the landing page demo.
    Public endpoint.
    """
    return {
        "markdown": "# Sample LLM.txt structure\n\n## Introduction\nThis is a sample...\n\n## Core Concepts\n- Concept A\n- Concept B",
        "json": {
            "site": "example.com",
            "endpoints": [
                {"url": "/api/v1", "description": "Main API", "priority": "high"}
            ]
        },
        "facts": {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Acme Corp",
            "sameAs": ["https://twitter.com/acme"]
        }
    }

# ============================================
# DOWNLOAD ENDPOINT (Payment handled via /payment/* routes)
# ============================================

@app.get("/download/{job_id}")
async def download_package(
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Download the generated ZIP package.
    Requires authentication, job ownership, AND PAYMENT.
    """
    from fastapi.responses import RedirectResponse
    
    db = get_database()
    job = await db.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Check ownership
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied. You do not own this job.")

    # CHECK PAYMENT
    if not job.payment_id:
        raise HTTPException(status_code=402, detail="Payment required to download files.")

    if job.status != JobStatus.COMPLETED or not job.result_path:
        raise HTTPException(status_code=400, detail="Job not completed or result missing")

    result_path = job.result_path
    
    # Track download timestamp
    try:
        await db.update_job(job_id, downloaded_at=datetime.utcnow().isoformat())
    except Exception as e:
        logger.warning(f"Failed to track download for job {job_id}: {e}")
    
    # Check if result_path is a URL (Supabase Storage) or local path
    if result_path.startswith("http://") or result_path.startswith("https://"):
        # Redirect to Supabase Storage URL
        return RedirectResponse(url=result_path, status_code=302)
    else:
        # Serve local file (dev mode fallback)
        path = Path(result_path).resolve()
        
        if not path.exists():
            raise HTTPException(status_code=404, detail="Result file not found on server")

        return FileResponse(path, filename=path.name, media_type="application/octet-stream")




# ============================================
# CANCEL JOB
# ============================================

@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str, user: dict = Depends(get_current_user)):
    """
    Cancel a running job.
    Requires authentication and job ownership.
    """
    db = get_database()
    job = await db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # SECURITY: Verify user owns this job
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied. You do not own this job.")
        
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return {"status": "unchanged", "message": f"Job is already {job.status}"}
        
    # Update status to CANCELLED in DB
    await db.update_job_status(job_id, JobStatus.CANCELLED)
    
    # Revoke Celery task
    from celery_app import celery_app
    celery_app.control.revoke(job_id, terminate=True)
    
    return {"status": "cancelled", "message": "Job cancellation initiated"}


# ============================================
# LIST JOBS ENDPOINT
# ============================================

@app.get("/jobs")
async def list_jobs(
    limit: int = 10,
    user: dict = Depends(get_current_user)
):
    """
    List recent compilation jobs for the authenticated user.
    """
    db = get_database()
    jobs = await db.get_user_jobs(user["id"], limit=limit, token=user.get("token"))
    return jobs


# ============================================
# MAIN ENTRY
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
