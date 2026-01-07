-- Trial Codes Database Schema (Final Fix V2)
-- Run this in your Supabase SQL Editor

-- 1. Create Tables (Safe if exist)
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
    code TEXT NOT NULL REFERENCES trial_codes(code) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_email TEXT,
    UNIQUE(code, user_id, job_id)
);

CREATE TABLE IF NOT EXISTS early_access_requests (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    trial_code TEXT REFERENCES trial_codes(code),
    job_id TEXT NOT NULL,
    linkedin_url TEXT,
    twitter_url TEXT,
    role TEXT,
    company TEXT,
    website_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    testimonial_status TEXT NOT NULL DEFAULT 'pending',
    testimonial_text TEXT,
    followup_at TIMESTAMPTZ,
    testimonial_received_at TIMESTAMPTZ,
    UNIQUE(user_id)
);

-- 2. Indexes (Safe if exist)
CREATE INDEX IF NOT EXISTS idx_trial_codes_active ON trial_codes(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_trial_redemptions_user ON trial_redemptions(user_id);
CREATE INDEX IF NOT EXISTS idx_early_access_status ON early_access_requests(testimonial_status);

-- 3. Enable RLS
ALTER TABLE trial_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE early_access_requests ENABLE ROW LEVEL SECURITY;

-- 4. CLEAN UP ALL POLICIES (Brute Force Drop)
DO $$ 
BEGIN
    -- trial_codes policies
    DROP POLICY IF EXISTS "Trial codes are readable by authenticated users" ON trial_codes;
    DROP POLICY IF EXISTS "Only service role can modify trial codes" ON trial_codes;
    DROP POLICY IF EXISTS "Trial codes are readable by all" ON trial_codes;
    DROP POLICY IF EXISTS "Allow all for service role on trial codes" ON trial_codes;
    DROP POLICY IF EXISTS "Users can create trial codes" ON trial_codes;

    -- trial_redemptions policies
    DROP POLICY IF EXISTS "Users can see their own redemptions" ON trial_redemptions;
    DROP POLICY IF EXISTS "Only service role can create redemptions" ON trial_redemptions;
    DROP POLICY IF EXISTS "Allow all for service role on trial redemptions" ON trial_redemptions;

    -- early_access_requests policies
    DROP POLICY IF EXISTS "Users can see their own early access" ON early_access_requests;
    DROP POLICY IF EXISTS "Service role can manage early access" ON early_access_requests;
    DROP POLICY IF EXISTS "Allow all for service role on early access" ON early_access_requests;
    DROP POLICY IF EXISTS "Users can create early access requests" ON early_access_requests;
END $$;

-- 5. RE-CREATE POLICIES (With ANON permission)

-- trial_codes policies
CREATE POLICY "Trial codes are readable by all"
    ON trial_codes FOR SELECT
    TO authenticated, service_role, anon
    USING (true);

-- ALLOW USERS (and Backend with Anon Key) TO CREATE TRIAL CODES
CREATE POLICY "Users can create trial codes"
    ON trial_codes FOR INSERT
    TO authenticated, anon, service_role
    WITH CHECK (true);

CREATE POLICY "Allow all for service role on trial codes"
    ON trial_codes FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- trial_redemptions policies
CREATE POLICY "Users can see their own redemptions"
    ON trial_redemptions FOR SELECT
    TO authenticated, anon
    USING (auth.uid()::text = user_id);

CREATE POLICY "Allow all for service role on trial redemptions"
    ON trial_redemptions FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- early_access_requests policies
CREATE POLICY "Users can see their own early access"
    ON early_access_requests FOR SELECT
    TO authenticated, anon
    USING (auth.uid()::text = user_id);

-- ALLOW USERS (and Backend with Anon Key) TO CREATE EARLY ACCESS REQUESTS
CREATE POLICY "Users can create early access requests"
    ON early_access_requests FOR INSERT
    TO authenticated, anon, service_role
    WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Allow all for service role on early access"
    ON early_access_requests FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
