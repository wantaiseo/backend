"""
CiteKit – Celery Tasks
Background job orchestration for the compile pipeline
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from urllib.parse import urlparse
from celery import shared_task

# Configure logging
logger = logging.getLogger("geo-compiler.tasks")


from celery_app import celery_app
from config import get_settings
from database import get_database
from discovery import DiscoveryEngine
from extractor import ContentExtractor
from classifier import PageClassifier
from synthesizer import KnowledgeSynthesizer
from packager import Packager
from benchmark import run_benchmark
from models import CompileJob, JobStatus, PageData
from citation_scorer import CitationScorer
from platform_detector import detect_platform, get_deployment_guide_id


def run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def check_cancellation(job_id: str):
    """Check if the job has been cancelled."""
    db = get_database()
    job = await db.get_job(job_id)
    if job and job.status == JobStatus.CANCELLED:
        raise Exception("Job cancelled by user")

@celery_app.task(bind=True, max_retries=3)
def compile_website_task(self, job_id: str, url: str, crawl_depth: str = "auto", include_subdomains: bool = False, competitors: list = None, user_email: str = None):
    """
    Main compile task orchestrating the full pipeline.
    """
    if competitors is None:
        competitors = []
    db = get_database()

    try:
        # Check cancellation
        run_async(check_cancellation(job_id))

        # ============================================
        # PHASE 1: DISCOVERY
        # ============================================
        run_async(db.update_job_status(job_id, JobStatus.DISCOVERING))

        parsed = urlparse(url)
        domain = parsed.netloc
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Fetch live robots.txt for analysis
        robots_txt_content = None
        try:
            import requests
            print(f"Checking for robots.txt at {base_url}/robots.txt...")
            resp = requests.get(f"{base_url}/robots.txt", timeout=4)
            if resp.status_code == 200:
                robots_txt_content = resp.text
                print("✅ Found robots.txt")
            else:
                print("❌ No robots.txt found")
        except Exception as e:
            print(f"Failed to fetch robots.txt: {e}")

        # Determine max pages based on crawl_depth (cost-optimized)
        max_pages = None
        if crawl_depth == "shallow":
            max_pages = 20
        elif crawl_depth == "deep":
            max_pages = 100  # Reduced from 500 for profitability
        # "auto" uses default (50) from settings

        discovery = DiscoveryEngine(base_url, include_subdomains)
        discovered_urls = run_async(discovery.discover(max_pages=max_pages))

        # Save discovered URLs
        run_async(db.save_discovered_urls(job_id, discovered_urls))

        total_pages = len(discovered_urls)
        run_async(db.update_job(job_id, total_pages=total_pages))

        # ============================================
        # PHASE 2: CONTENT EXTRACTION
        # ============================================
        run_async(check_cancellation(job_id))
        run_async(db.update_job_status(job_id, JobStatus.EXTRACTING))

        extractor = ContentExtractor()
        pages: list[PageData] = []

        for idx, page_url in enumerate(discovered_urls):
            run_async(check_cancellation(job_id))
            page_data = run_async(extractor.process_page(page_url))
            if page_data:
                pages.append(page_data)

            # Update progress
            progress = int((idx + 1) / total_pages * 30)  # 0-30% for extraction
            run_async(db.update_job(job_id, progress=progress))

        # ============================================
        # PHASE 3: CLASSIFICATION (batched for cost efficiency)
        # ============================================
        run_async(check_cancellation(job_id))
        run_async(db.update_job_status(job_id, JobStatus.CLASSIFYING))

        classifier = PageClassifier()
        
        # Use batched classification to reduce API calls
        pages = run_async(classifier.classify_pages(pages))
        run_async(db.update_job(job_id, progress=50))

        # Save classified pages to database
        for idx, page in enumerate(pages):
            run_async(check_cancellation(job_id))
            run_async(db.save_page(job_id, page))
            
            # Update progress
            progress = 50 + int((idx + 1) / len(pages) * 10)  # 50-60%
            run_async(db.update_job(job_id, progress=progress))

        # ============================================
        # PHASE 3.5: PLATFORM DETECTION
        # ============================================
        platform_info = None
        detected_platform = "custom"
        detected_hosting = None
        
        # Use homepage or first page for detection
        homepage = next((p for p in pages if p.classification.get('page_type') == 'homepage'), None)
        detection_page = homepage or (pages[0] if pages else None)
        
        if detection_page and detection_page.content:
            try:
                platform_info = detect_platform(
                    html=detection_page.content,
                    headers={},  # Headers not stored in PageData, but can be added
                    url=detection_page.url
                )
                detected_platform = platform_info.platform
                detected_hosting = platform_info.hosting
                
                print(f"[Task] Platform detected: {platform_info.platform_name} (confidence: {platform_info.confidence:.0%})")
                if platform_info.hosting:
                    print(f"[Task] Hosting detected: {platform_info.hosting}")
            except Exception as e:
                print(f"[Task] Platform detection failed (non-critical): {e}")

        # ============================================
        # PHASE 4: SYNTHESIS
        # ============================================
        run_async(check_cancellation(job_id))
        run_async(db.update_job_status(job_id, JobStatus.SYNTHESIZING))

        synthesizer = KnowledgeSynthesizer()

        # Generate llm.txt
        llm_txt = run_async(synthesizer.generate_llm_txt(domain, pages))
        run_async(db.update_job(job_id, progress=70))

        # Generate MCP JSON
        mcp = run_async(synthesizer.generate_mcp_json(domain, pages))
        run_async(db.update_job(job_id, progress=80))

        # Generate enhanced facts.jsonld with sameAs + pricing
        facts, extracted_facts = synthesizer.generate_facts_jsonld(pages)
        run_async(db.update_job(job_id, progress=85))

        # ============================================
        # PHASE 5: READINESS SCORING
        # ============================================
        citation_scorer = CitationScorer(pages, facts, mcp, domain, robots_txt=robots_txt_content)
        readiness_result = citation_scorer.calculate_score()
        
        print(f"[Task] Readiness Score: {readiness_result.total}/100 (Grade: {readiness_result.grade})")
        print(f"[Task] Action items: {len(readiness_result.action_items)}, Issues: {len(readiness_result.issues)}")

        # ============================================
        # PHASE 6: PACKAGING + AUDIT + BENCHMARK
        # ============================================
        run_async(check_cancellation(job_id))
        run_async(db.update_job_status(job_id, JobStatus.PACKAGING))

        # Run competitor benchmark if competitors provided
        benchmark_report = ""
        if competitors:
            print(f"Benchmarking {len(competitors)} competitors...")
            try:
                benchmark_report = run_async(run_benchmark(domain, readiness_result.total, competitors))
            except Exception as e:
                print(f"Benchmark failed (non-critical): {e}")

        # Prepare readiness score data for packager
        citation_score_data = {
            "total": readiness_result.total,
            "grade": readiness_result.grade,
            "breakdown": readiness_result.breakdown,
            "quick_wins": [
                {"action": w.action if hasattr(w, 'action') else w.get('action', ''), 
                 "why": w.why if hasattr(w, 'why') else w.get('why', ''), 
                 "impact": w.why if hasattr(w, 'why') else w.get('why', ''), 
                 "time": w.time if hasattr(w, 'time') else w.get('time', ''), 
                 "file": w.file if hasattr(w, 'file') else w.get('file', '')}
                for w in readiness_result.action_items
            ],
            "interpretation": readiness_result.summary
        }
        
        # Convert issues to dicts (handle both object and dict formats)
        citation_issues = [
            {
                "severity": i.severity if hasattr(i, 'severity') else i.get('severity', ''),
                "category": i.category if hasattr(i, 'category') else i.get('category', ''),
                "title": i.issue if hasattr(i, 'issue') else i.get('issue', ''),
                "description": i.why_it_matters if hasattr(i, 'why_it_matters') else i.get('why_it_matters', ''),
                "affected_urls": []
            }
            for i in readiness_result.issues
        ]

        # Save audit.json for frontend display (pre-payment)
        settings = get_settings()

        job_dir = os.path.join(settings.output_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Run structured benchmark for frontend (if competitors provided)
        benchmark_data = None
        if competitors:
            try:
                from benchmark import run_full_benchmark
                # Get homepage HTML for your site schema extraction
                homepage_html = ""
                homepage = next((p for p in pages if p.classification.get('page_type') == 'homepage'), None)
                if homepage and homepage.content:
                    homepage_html = homepage.content
                
                benchmark_data = run_async(run_full_benchmark(
                    domain,
                    readiness_result.total,
                    homepage_html,
                    competitors
                ))
                print(f"[Task] Benchmark complete. Your rank: #{benchmark_data.get('your_rank', '?')}")
            except Exception as e:
                print(f"[Task] Structured benchmark failed (non-critical): {e}")
        
        audit_data = {
           "score": citation_score_data,
           "issues": citation_issues,
           "benchmark": benchmark_data,  # Structured data for frontend
           "platform": {
               "detected": detected_platform,
               "name": platform_info.platform_name if platform_info else "Custom/Static",
               "hosting": detected_hosting,
               "confidence": platform_info.confidence if platform_info else 0.5,
               "guide_id": get_deployment_guide_id(platform_info) if platform_info else "cpanel"
           },
           "generated_at": datetime.utcnow().isoformat()
        }
        
        with open(os.path.join(job_dir, "audit.json"), "w") as f:
            json.dump(audit_data, f, indent=2)

        packager = Packager()
        zip_path, errors, geo_score = packager.generate_package(
            job_id, domain, llm_txt, mcp, pages,
            facts=facts,
            extracted_facts=extracted_facts,
            benchmark_report=benchmark_report,
            citation_score_data=citation_score_data,
            citation_issues=citation_issues,
            platform_info=audit_data.get("platform")
        )

        if errors:
            run_async(db.update_job_status(
                job_id,
                JobStatus.FAILED,
                error="; ".join(errors)
            ))
            return {"status": "failed", "errors": errors}

        # ============================================
        # UPLOAD TO STORAGE & COMPLETE
        # ============================================
        
        # Upload to Supabase Storage (job-results bucket)
        try:
            public_url = db.upload_file("job-results", f"{job_id}.zip", zip_path)
            print(f"✅ Uploaded result to storage: {public_url}")
        except Exception as e:
            print(f"❌ Storage upload failed but job completed: {e}")
            public_url = zip_path # Fallback to local path if storage fails (dev mode)

        # Compile Output Data for DB Storage (Robust Preview)
        output_data = {
            "audit": audit_data,
            "mcp": mcp.model_dump() if mcp else None,
            "facts": facts,
            "llm_txt": llm_txt
        }

        run_async(db.update_job(
            job_id,
            status="completed",
            progress=100,
            result_path=public_url,
            geo_score=geo_score,
            completed_at=datetime.utcnow().isoformat(),
            output_data=output_data
        ))

        # 📧 NOTE: Email is now sent AFTER PAYMENT in payments.py, not here.
        # Compilation is free - email is only sent when user pays and unlocks the file.


        return {
            "status": "completed",
            "job_id": job_id,
            "result_path": zip_path,
            "total_pages": len(pages),
            "geo_score": geo_score
        }

    except ValueError as e:
        # User input errors (like SSRF blocking) - don't retry, fail immediately
        run_async(db.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=f"Invalid URL: {str(e)}"
        ))
        return {"status": "failed", "error": str(e)}

    except Exception as e:
        run_async(db.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e)
        ))
        if "cancelled" in str(e).lower():
            run_async(db.update_job_status(job_id, JobStatus.CANCELLED))
            return {"status": "cancelled"}
        raise self.retry(exc=e, countdown=60)
