"""
CiteKit – Supabase Database Layer
"""

from supabase import create_client, Client
from config import get_settings
from models import CompileJob, JobStatus, PageData
from typing import Optional
import json


class Database:
    """Supabase database wrapper for persistence"""

    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.PAYMENTS_FILE = "payments.json"

    def _get_payment_id(self, job_id: str) -> Optional[str]:
        """Get payment ID from local file registry (Fallback for missing DB column)"""
        try:
            with open(self.PAYMENTS_FILE, "r") as f:
                payments = json.load(f)
                return payments.get(job_id)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _set_payment_id(self, job_id: str, payment_id: str):
        """Save payment ID to local file registry"""
        try:
            try:
                with open(self.PAYMENTS_FILE, "r") as f:
                    payments = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                payments = {}
            
            payments[job_id] = payment_id
            
            with open(self.PAYMENTS_FILE, "w") as f:
                json.dump(payments, f)
        except Exception as e:
            print(f"Failed to save payment registry: {e}")

    # ============================================
    # STORAGE
    # ============================================

    def upload_file(self, bucket: str, path: str, file_path_local: str) -> str:
        """Upload a file to Supabase Storage and return public URL"""
        try:
            with open(file_path_local, 'rb') as f:
                self.client.storage.from_(bucket).upload(
                    file=f,
                    path=path,
                    file_options={"content-type": "application/zip", "upsert": "true"}
                )
            
            # Get Public URL
            return self.client.storage.from_(bucket).get_public_url(path)
        except Exception as e:
            print(f"Failed to upload file to storage: {e}")
            raise e

    # ============================================
    # JOBS TABLE
    # ============================================
    
    # Columns that exist in the application model but NOT in the Supabase schema
    _NON_DB_COLUMNS = {"payment_id", "geo_score"}

    async def create_job(self, job: CompileJob, token: str = None) -> CompileJob:
        """Create a new compile job with Local Fallback"""
        data = job.model_dump()
        
        # Allowed columns for Supabase
        allowed_columns = {'job_id', 'url', 'status', 'progress', 'total_pages', 'created_at', 'completed_at', 'error', 'result_path', 'user_id'}
        
        # Cache shadow fields
        payment_id_cache = data.get("payment_id")
        geo_score_cache = data.get("geo_score")
        
        filtered_data = {k: v for k, v in data.items() if k in allowed_columns and v is not None}
            
        current_client = self.get_user_client(token) if token else self.client
        
        try:
            # 1. Try Supabase
            result = current_client.table("jobs").insert(filtered_data).execute()
            if result.data:
                job_obj = CompileJob(**result.data[0])
            else:
                 # Fallback to local if insert succeeded but returned no data (weird RLS)
                 self._save_local_job(filtered_data)
                 job_obj = job
        except Exception as e:
            # 2. Fallback to Local JSON
            print(f"Supabase insert failed ({e}), using Local JSON fallback...")
            self._save_local_job(filtered_data)
            job_obj = job
        
        # Identify Object
        if payment_id_cache:
            self._set_payment_id(job_obj.job_id, payment_id_cache)
            job_obj.payment_id = payment_id_cache
        
        job_obj.geo_score = geo_score_cache
        return job_obj

    async def get_job(self, job_id: str) -> Optional[CompileJob]:
        """Get job by ID (Supabase + Local)"""
        try:
            result = self.client.table("jobs").select("*").eq("job_id", job_id).execute()
            if result.data:
                job = CompileJob(**result.data[0])
                job.payment_id = self._get_payment_id(job_id)
                return job
        except Exception:
            pass
            
        # Try Local
        local_job = self._get_local_job(job_id)
        if local_job:
            job = CompileJob(**local_job)
            job.payment_id = self._get_payment_id(job_id)
            return job
            
        return None

    async def update_job(self, job_id: str, **updates) -> Optional[CompileJob]:
        """Update job (Supabase + Local)"""
        if "payment_id" in updates:
            self._set_payment_id(job_id, updates["payment_id"])
            
        db_updates = {k: v for k, v in updates.items() if k not in self._NON_DB_COLUMNS}
        
        # Try Supabase
        try:
            if db_updates:
                self.client.table("jobs").update(db_updates).eq("job_id", job_id).execute()
        except Exception as e:
            print(f"Supabase update failed ({e}), updating Local JSON...")
            
        # Always update local (to ensure sync if we fell back previously)
        if db_updates:
            self._update_local_job(job_id, db_updates)
            
        return await self.get_job(job_id)

    async def get_user_jobs(self, user_id: str, limit: int = 50, token: str = None) -> list[CompileJob]:
        """Get jobs for a user (Merge Supabase + Local)"""
        jobs = []
        
        # 1. Fetch Supabase
        try:
            current_client = self.get_user_client(token) if token else self.client
            response = current_client.table("jobs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            for row in response.data:
                job = CompileJob(**row)
                job.payment_id = self._get_payment_id(job.job_id)
                jobs.append(job)
        except Exception as e:
            print(f"Supabase list failed ({e})")
            
        # 2. Fetch Local and Merge
        local_jobs = self._get_all_local_jobs()
        for l_job in local_jobs:
            # Simple dedup: if not in list
            if l_job.get("user_id") == user_id:
                if not any(j.job_id == l_job["job_id"] for j in jobs):
                    job = CompileJob(**l_job)
                    job.payment_id = self._get_payment_id(job.job_id)
                    jobs.append(job)
        
        # Sort combined list
        jobs.sort(key=lambda x: x.created_at or "", reverse=True)
        return jobs[:limit]

    # ============================================
    # 📂 LOCAL JSON FALLBACK HELPERS
    # ============================================
    LOCAL_DB_FILE = "jobs.json"

    def _load_local_db(self) -> list:
        import json
        import os
        if not os.path.exists(self.LOCAL_DB_FILE):
             return []
        try:
            with open(self.LOCAL_DB_FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def _save_local_job(self, job_data: dict):
        import json
        data = self._load_local_db()
        # Remove existing if ID matches
        data = [j for j in data if j["job_id"] != job_data["job_id"]]
        data.append(job_data)
        with open(self.LOCAL_DB_FILE, "w") as f:
            json.dump(data, f, default=str)

    def _update_local_job(self, job_id: str, updates: dict):
        import json
        data = self._load_local_db()
        for job in data:
            if job["job_id"] == job_id:
                job.update(updates)
        with open(self.LOCAL_DB_FILE, "w") as f:
            json.dump(data, f, default=str)

    def _get_local_job(self, job_id: str):
        data = self._load_local_db()
        for job in data:
            if job["job_id"] == job_id:
                return job
        return None

    def _get_all_local_jobs(self):
        return self._load_local_db()


    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: int = None,
        error: str = None
    ) -> Optional[CompileJob]:
        """Update job status and optionally progress/error"""
        # Defensive: Handle if status is passed as string instead of Enum
        status_value = status.value if hasattr(status, "value") else str(status)
        
        updates = {"status": status_value}
        if progress is not None:
            updates["progress"] = progress
        if error is not None:
            updates["error"] = error
        return await self.update_job(job_id, **updates)

    def get_user_client(self, token: str) -> Client:
        """
        Get a Supabase client authenticated as the user.
        This ensures RLS policies are respected using the user's JWT.
        """
        settings = get_settings()
        # Create a fresh client or clone? Fresh is safer for auth context.
        client = create_client(settings.supabase_url, settings.supabase_key)
        client.postgrest.auth(token)
        return client

    def get_service_client(self) -> Client:
        """
        Get a Supabase client with SERVICE_ROLE privileges.
        This bypasses RLS policies. USE WITH CAUTION.
        """
        settings = get_settings()
        # Use service role key if available, otherwise fallback to default key (which might be service role)
        key = settings.supabase_service_role_key or settings.supabase_key
        return create_client(settings.supabase_url, key)

    async def get_user_job_count(self, user_id: str) -> int:
        """Get count of jobs for a user"""
        result = (
            self.client.table("jobs")
            .select("*", count="exact", head=True)
            .eq("user_id", user_id)
            .execute()
        )
        return result.count if result.count is not None else 0

    async def get_user_free_audit_count(self, user_id: str) -> int:
        """
        Get count of FREE audits (jobs without payment) for a user.
        A job is considered "free" if there's no paid payment_order for it.
        """
        try:
            # 1. Get total job count for user
            total_jobs_result = (
                self.client.table("jobs")
                .select("*", count="exact", head=True)
                .eq("user_id", user_id)
                .execute()
            )
            total_jobs = total_jobs_result.count or 0
            
            # 2. Get paid job count for user
            paid_jobs_result = (
                self.client.table("payment_orders")
                .select("*", count="exact", head=True)
                .eq("user_id", user_id)
                .eq("status", "paid")
                .execute()
            )
            paid_jobs = paid_jobs_result.count or 0
            
            # Free audits = total jobs - paid jobs
            free_count = max(0, total_jobs - paid_jobs)
            return free_count
            
        except Exception as e:
            print(f"Error counting free audits: {e}")
            # On error, be permissive - allow the audit
            return 0

    async def get_user_paid_job_count(self, user_id: str) -> int:
        """
        Get count of PAID jobs for a user.
        Used for determining if user can create more free audits.
        """
        try:
            result = (
                self.client.table("payment_orders")
                .select("*", count="exact", head=True)
                .eq("user_id", user_id)
                .eq("status", "paid")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            print(f"Error counting paid jobs: {e}")
            return 0

    async def can_user_create_audit(self, user_id: str, free_audit_limit: int = 2) -> tuple[bool, str]:
        """
        Check if user can create a new audit based on free audit limit.
        
        Rules:
        - Users get `free_audit_limit` free audits (default: 2)
        - After using free audits, they need at least 1 paid job to unlock more
        - Each paid job unlocks 1 additional audit slot
        
        Formula: allowed_audits = free_audit_limit + paid_count
        
        Returns: (can_create: bool, reason: str)
        """
        try:
            # Get counts
            total_jobs_result = (
                self.client.table("jobs")
                .select("*", count="exact", head=True)
                .eq("user_id", user_id)
                .execute()
            )
            total_jobs = total_jobs_result.count or 0
            
            paid_jobs_result = (
                self.client.table("payment_orders")
                .select("*", count="exact", head=True)
                .eq("user_id", user_id)
                .eq("status", "paid")
                .execute()
            )
            paid_count = paid_jobs_result.count or 0
            
            # Calculate allowed audits
            # Users get free_audit_limit free + 1 for each payment
            allowed_audits = free_audit_limit + paid_count
            
            print(f"📊 Audit limit check: user={user_id[:8]}..., total_jobs={total_jobs}, paid={paid_count}, allowed={allowed_audits}")
            
            if total_jobs < allowed_audits:
                return True, "OK"
            else:
                remaining_free = max(0, free_audit_limit - (total_jobs - paid_count))
                if paid_count == 0:
                    return False, f"You've used your {free_audit_limit} free audits. Please purchase a previous audit to unlock more."
                else:
                    return False, f"You've used all your audit credits ({allowed_audits} total). Purchase another audit to continue."
                    
        except Exception as e:
            print(f"Error in audit limit check: {e}")
            # On database error, be permissive
            return True, "OK"

    async def find_recent_completed_job(self, url: str) -> Optional[CompileJob]:
        """Find a completed job for this URL (Simple Caching)"""
        result = (
             self.client.table("jobs")
             .select("*")
             .eq("url", url)
             .eq("status", "completed")
             .order("created_at", desc=True)
             .limit(1)
             .execute()
        )
        if result.data:
            job = CompileJob(**result.data[0])
            job.payment_id = self._get_payment_id(job.job_id)
            return job
        return None

    # ============================================
    # PAGES TABLE (with local fallback)
    # ============================================
    
    PAGES_FILE = "pages.json"

    def _load_local_pages(self) -> dict:
        """Load pages from local file"""
        import os
        if not os.path.exists(self.PAGES_FILE):
            return {}
        try:
            with open(self.PAGES_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_local_page(self, job_id: str, page_data: dict):
        """Save page to local file"""
        data = self._load_local_pages()
        if job_id not in data:
            data[job_id] = []
        data[job_id].append(page_data)
        with open(self.PAGES_FILE, "w") as f:
            json.dump(data, f, default=str)

    async def save_page(self, job_id: str, page: PageData) -> None:
        """Save extracted page data (with fallback)"""
        page_data = {
            "job_id": job_id,
            "url": page.url,
            "title": page.title,
            "description": page.description,
            "content": page.content,
            "headings": page.headings,
            "classification": page.classification
        }
        try:
            self.client.table("pages").insert(page_data).execute()
        except Exception as e:
            print(f"Supabase pages insert failed ({e}), using local fallback...")
            self._save_local_page(job_id, page_data)

    async def get_pages(self, job_id: str) -> list[PageData]:
        """Get all pages for a job (with fallback)"""
        try:
            result = self.client.table("pages").select("*").eq("job_id", job_id).execute()
            return [PageData(**row) for row in result.data]
        except Exception as e:
            print(f"Supabase get_pages failed ({e}), using local fallback...")
            data = self._load_local_pages()
            if job_id in data:
                return [PageData(**row) for row in data[job_id]]
            return []

    # ============================================
    # DISCOVERED URLS TABLE (with local fallback)
    # ============================================
    
    DISCOVERED_URLS_FILE = "discovered_urls.json"

    def _load_discovered_urls(self) -> dict:
        """Load discovered URLs from local file"""
        import os
        if not os.path.exists(self.DISCOVERED_URLS_FILE):
            return {}
        try:
            with open(self.DISCOVERED_URLS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_discovered_urls_local(self, job_id: str, urls: list[str]):
        """Save discovered URLs to local file"""
        data = self._load_discovered_urls()
        if job_id not in data:
            data[job_id] = {}
        for url in urls:
            if url not in data[job_id]:
                data[job_id][url] = "pending"
        with open(self.DISCOVERED_URLS_FILE, "w") as f:
            json.dump(data, f, default=str)

    async def save_discovered_urls(self, job_id: str, urls: list[str]) -> None:
        """Save discovered URLs for a job (with fallback)"""
        try:
            data = [{"job_id": job_id, "url": url, "status": "pending"} for url in urls]
            if data:
                # Simple insert instead of upsert to avoid constraint issues
                self.client.table("discovered_urls").insert(data).execute()
        except Exception as e:
            print(f"Supabase discovered_urls insert failed ({e}), using local fallback...")
            self._save_discovered_urls_local(job_id, urls)

    async def get_pending_urls(self, job_id: str, limit: int = 10) -> list[str]:
        """Get pending URLs to crawl (with fallback)"""
        try:
            result = (
                self.client.table("discovered_urls")
                .select("url")
                .eq("job_id", job_id)
                .eq("status", "pending")
                .limit(limit)
                .execute()
            )
            return [row["url"] for row in result.data]
        except Exception as e:
            print(f"Supabase get_pending_urls failed ({e}), using local fallback...")
            data = self._load_discovered_urls()
            if job_id in data:
                pending = [url for url, status in data[job_id].items() if status == "pending"]
                return pending[:limit]
            return []

    async def mark_url_processed(self, job_id: str, url: str) -> None:
        """Mark URL as processed (with fallback)"""
        try:
            (
                self.client.table("discovered_urls")
                .update({"status": "processed"})
                .eq("job_id", job_id)
                .eq("url", url)
                .execute()
            )
        except Exception as e:
            print(f"Supabase mark_url_processed failed ({e}), using local fallback...")
            data = self._load_discovered_urls()
            if job_id in data and url in data[job_id]:
                data[job_id][url] = "processed"
                with open(self.DISCOVERED_URLS_FILE, "w") as f:
                    json.dump(data, f, default=str)

    # ============================================
    # PAYMENT ORDERS TABLE
    # ============================================
    
    async def create_payment_order(
        self, 
        job_id: str, 
        user_id: str,
        razorpay_order_id: str, 
        amount: int,
        currency: str = "INR"
    ) -> dict:
        """Create a new payment order record"""
        from datetime import datetime
        
        order_data = {
            "job_id": job_id,
            "user_id": user_id,
            "razorpay_order_id": razorpay_order_id,
            "amount": amount,
            "currency": currency,
            "status": "created",
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client.table("payment_orders").insert(order_data).execute()
            if result.data:
                print(f"✅ Created payment order: {razorpay_order_id}")
                return result.data[0]
        except Exception as e:
            print(f"Failed to create payment order: {e}")
            raise e
        
        return order_data
    
    async def get_pending_payment_order(self, job_id: str) -> Optional[dict]:
        """Get existing pending payment order for a job (for idempotency)"""
        try:
            result = (
                self.client.table("payment_orders")
                .select("*")
                .eq("job_id", job_id)
                .eq("status", "created")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"Error fetching pending payment order: {e}")
        return None
    
    async def get_payment_order_by_razorpay_id(self, razorpay_order_id: str) -> Optional[dict]:
        """Get payment order by Razorpay order ID"""
        try:
            result = (
                self.client.table("payment_orders")
                .select("*")
                .eq("razorpay_order_id", razorpay_order_id)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"Error fetching payment order: {e}")
        return None
    
    async def get_payment_order_by_job_id(self, job_id: str) -> Optional[dict]:
        """Get the most recent payment order for a job"""
        try:
            result = (
                self.client.table("payment_orders")
                .select("*")
                .eq("job_id", job_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"Error fetching payment order by job_id: {e}")
        return None
    
    async def update_payment_order_status(
        self,
        razorpay_order_id: str,
        status: str,
        razorpay_payment_id: str = None
    ) -> Optional[dict]:
        """Update payment order status (created -> paid/failed)"""
        from datetime import datetime
        
        update_data = {"status": status}
        
        if razorpay_payment_id:
            update_data["razorpay_payment_id"] = razorpay_payment_id
        
        if status == "paid":
            update_data["paid_at"] = datetime.utcnow().isoformat()
        
        try:
            result = (
                self.client.table("payment_orders")
                .update(update_data)
                .eq("razorpay_order_id", razorpay_order_id)
                .execute()
            )
            if result.data:
                print(f"✅ Updated payment order {razorpay_order_id} -> {status}")
                return result.data[0]
        except Exception as e:
            print(f"Failed to update payment order: {e}")
        return None
    
    async def get_payment_statistics(self, user_id: str = None) -> dict:
        """Get payment statistics (for admin/analytics)"""
        try:
            query = self.client.table("payment_orders").select("*", count="exact")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            # Get paid orders
            paid_result = query.eq("status", "paid").execute()
            
            total_revenue = sum(order.get("amount", 0) for order in (paid_result.data or []))
            
            return {
                "total_orders": paid_result.count or 0,
                "total_revenue_paise": total_revenue,
                "total_revenue_inr": total_revenue / 100
            }
        except Exception as e:
            print(f"Error fetching payment statistics: {e}")
            return {"total_orders": 0, "total_revenue_paise": 0, "total_revenue_inr": 0}

    # ============================================
    # WORDPRESS INTEGRATIONS
    # ============================================
    
    WP_CONNECTIONS_FILE = "wordpress_connections.json"
    
    def _load_wp_connections(self) -> dict:
        """Load WordPress connections from local file"""
        import os
        if not os.path.exists(self.WP_CONNECTIONS_FILE):
            return {}
        try:
            with open(self.WP_CONNECTIONS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def _save_wp_connections(self, data: dict):
        """Save WordPress connections to local file"""
        with open(self.WP_CONNECTIONS_FILE, "w") as f:
            json.dump(data, f, default=str)
    
    async def save_wordpress_connection(
        self, 
        user_id: str, 
        site_url: str, 
        site_key: str
    ) -> dict:
        """Save a WordPress site connection for a user"""
        from datetime import datetime
        
        connection = {
            "user_id": user_id,
            "site_url": site_url,
            "site_key": site_key,  # Encrypted in production!
            "connected_at": datetime.utcnow().isoformat()
        }
        
        # Try Supabase first
        try:
            # Check if exists
            existing = (
                self.client.table("wordpress_connections")
                .select("*")
                .eq("user_id", user_id)
                .eq("site_url", site_url)
                .execute()
            )
            
            if existing.data:
                # Update
                result = (
                    self.client.table("wordpress_connections")
                    .update({"site_key": site_key, "connected_at": connection["connected_at"]})
                    .eq("user_id", user_id)
                    .eq("site_url", site_url)
                    .execute()
                )
            else:
                # Insert
                result = self.client.table("wordpress_connections").insert(connection).execute()
            
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"Supabase wordpress_connections failed ({e}), using local fallback...")
        
        # Local fallback
        data = self._load_wp_connections()
        if user_id not in data:
            data[user_id] = []
        
        # Update or add
        updated = False
        for conn in data[user_id]:
            if conn["site_url"] == site_url:
                conn["site_key"] = site_key
                conn["connected_at"] = connection["connected_at"]
                updated = True
                break
        
        if not updated:
            data[user_id].append(connection)
        
        self._save_wp_connections(data)
        return connection
    
    async def get_wordpress_connections(self, user_id: str) -> list:
        """Get all WordPress connections for a user"""
        try:
            result = (
                self.client.table("wordpress_connections")
                .select("site_url, connected_at")  # Don't return site_key!
                .eq("user_id", user_id)
                .execute()
            )
            if result.data:
                return result.data
        except Exception as e:
            print(f"Supabase get_wordpress_connections failed ({e}), using local fallback...")
        
        # Local fallback
        data = self._load_wp_connections()
        if user_id in data:
            # Don't return site_key for security
            return [{"site_url": c["site_url"], "connected_at": c["connected_at"]} for c in data[user_id]]
        return []
    
    async def get_wordpress_connection(self, user_id: str, site_url: str) -> Optional[dict]:
        """Get a specific WordPress connection (includes site_key for deployment)"""
        try:
            result = (
                self.client.table("wordpress_connections")
                .select("*")
                .eq("user_id", user_id)
                .eq("site_url", site_url)
                .execute()
            )
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"Supabase get_wordpress_connection failed ({e}), using local fallback...")
        
        # Local fallback
        data = self._load_wp_connections()
        if user_id in data:
            for conn in data[user_id]:
                if conn["site_url"] == site_url:
                    return conn
        return None


# Singleton instance
_db: Optional[Database] = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db

