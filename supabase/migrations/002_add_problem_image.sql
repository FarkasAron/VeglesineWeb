-- 002_add_problem_image.sql
-- Run in the Supabase SQL editor after 001_create_problems.sql

-- Add the primary display column
ALTER TABLE problems
    ADD COLUMN IF NOT EXISTS problem_image_url TEXT;

-- Drop the FTS trigger and column — not needed for now
DROP TRIGGER IF EXISTS problems_fts_trigger ON problems;
DROP FUNCTION IF EXISTS update_problems_fts();
ALTER TABLE problems DROP COLUMN IF EXISTS fts_vector;
