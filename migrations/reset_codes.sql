-- Reset Trial Codes Usage
-- Run this in Supabase SQL Editor to reset your testing usage

-- 1. Reset usage count to 0 for all codes
UPDATE trial_codes 
SET current_uses = 0;

-- 2. (Optional) Set max_uses to 100 for all codes if needed
-- UPDATE trial_codes SET max_uses = 100;

-- 3. Clear your test redemption history (so you can use it again)
DELETE FROM trial_redemptions; 
-- Be careful! This deletes ALL redemptions. Add WHERE user_id = '...' to be specific.

-- 4. Clear your test early access request
DELETE FROM early_access_requests;
-- Be careful! This deletes ALL requests. Add WHERE user_email = '...' to be specific.
