-- ============================================
-- GEO COMPILER - COMPLETE PRODUCTION DATABASE SETUP
-- Run this in your Supabase project's SQL Editor
-- Last Updated: 2025-12-28
-- ============================================

-- ============================================
-- 1. CREATE JOBS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.jobs (
    job_id UUID PRIMARY KEY,
    user_id UUID,
    url TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_pages INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    error TEXT,
    result_path TEXT
);

-- ============================================
-- 2. CREATE PAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES public.jobs(job_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    content TEXT,
    headings TEXT,
    classification TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 3. CREATE DISCOVERED URLS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.discovered_urls (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id TEXT,
    url TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 4. CREATE PAYMENT ORDERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.payment_orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id TEXT NOT NULL,
    user_id UUID NOT NULL,
    razorpay_order_id TEXT UNIQUE NOT NULL,
    razorpay_payment_id TEXT,
    amount INTEGER NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'paid', 'failed', 'refunded')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ
);

-- ============================================
-- 5. CREATE INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON public.jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON public.jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_url ON public.jobs(url);
CREATE INDEX IF NOT EXISTS idx_pages_job_id ON public.pages(job_id);
CREATE INDEX IF NOT EXISTS idx_discovered_urls_job_id ON public.discovered_urls(job_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_job_id ON public.payment_orders(job_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_razorpay_order_id ON public.payment_orders(razorpay_order_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_user_id ON public.payment_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON public.payment_orders(status);

-- ============================================
-- 6. ROW LEVEL SECURITY CONFIGURATION
-- ============================================

-- For MVP with backend using service_role key:
-- We DISABLE RLS since the backend handles authorization
-- The backend uses anon key for public reads and service_role for writes

ALTER TABLE public.jobs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.pages DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.discovered_urls DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_orders DISABLE ROW LEVEL SECURITY;

-- ============================================
-- 7. GRANT PERMISSIONS
-- ============================================
GRANT ALL ON public.jobs TO anon, authenticated, service_role;
GRANT ALL ON public.pages TO anon, authenticated, service_role;
GRANT ALL ON public.discovered_urls TO anon, authenticated, service_role;
GRANT ALL ON public.payment_orders TO anon, authenticated, service_role;

-- ============================================
-- 8. CREATE STORAGE BUCKET (Run separately in Dashboard)
-- ============================================
-- Go to Storage > New Bucket
-- Name: job-results
-- Public: Yes (or configure RLS for downloads)
--
-- Bucket Policy (if you want public downloads):
-- Allow SELECT for everyone, INSERT/UPDATE/DELETE for authenticated

-- ============================================
-- DONE! Verify with:
-- ============================================
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
