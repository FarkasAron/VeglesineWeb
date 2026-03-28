-- 001_create_problems.sql
-- Run ONCE in the Supabase SQL editor (Dashboard → SQL Editor → New query → Run)
-- before running scripts/06_import_to_db.py

-- ── problems table ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS problems (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at           TIMESTAMPTZ NOT NULL    DEFAULT now(),
    updated_at           TIMESTAMPTZ,

    -- Natural unique key: "{pdf_stem}__{problem_number:03d}__{sub_part or ''}"
    -- e.g. "e_mat_24okt_fl__009__c" or "k_mat_25okt_fl__001__"
    source_key           TEXT        NOT NULL UNIQUE,
    pdf_stem             TEXT        NOT NULL,
    pdf_filename         TEXT        NOT NULL,

    -- Exam metadata
    year                 SMALLINT    NOT NULL,
    exam_type            TEXT        NOT NULL,  -- 'kozep' | 'emelt'
    exam_session         TEXT        NOT NULL,  -- 'majus' | 'oktober' | 'februar'
    is_secondary_language BOOLEAN    NOT NULL   DEFAULT false,
    exam_part            TEXT,                  -- 'I' | 'II' | NULL
    problem_number       SMALLINT    NOT NULL,
    sub_part             VARCHAR(4),            -- 'a' | 'b' | 'c' | NULL

    -- Content
    statement_text       TEXT        NOT NULL   DEFAULT '',
    solution_text        TEXT,
    max_points           SMALLINT,

    -- Images  (formula placeholders stay as {{formula:filename.png}} in statement_text;
    --          formula_image_urls holds the ordered public CDN URLs in the same order)
    formula_image_urls   TEXT[]      NOT NULL   DEFAULT '{}',
    figure_urls          TEXT[]      NOT NULL   DEFAULT '{}',
    has_figure           BOOLEAN     NOT NULL   DEFAULT false,

    -- Review fields (set during Step 7 review — NULL until reviewed)
    difficulty_level     TEXT,        -- 'konnyu' | 'kozepes' | 'nehez'
    topic_tags           TEXT[]      NOT NULL   DEFAULT '{}',
    human_reviewed       BOOLEAN     NOT NULL   DEFAULT false,
    reviewed_by          TEXT,
    reviewed_at          TIMESTAMPTZ,

    -- Pipeline metadata
    ocr_used             BOOLEAN     NOT NULL   DEFAULT false,
    notes                TEXT        NOT NULL   DEFAULT '',

    -- Full-text search (auto-maintained by trigger below)
    fts_vector           TSVECTOR
);

-- ── Indexes ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS problems_year_type_idx
    ON problems (year, exam_type);

CREATE INDEX IF NOT EXISTS problems_reviewed_idx
    ON problems (human_reviewed);

CREATE INDEX IF NOT EXISTS problems_topic_idx
    ON problems USING GIN (topic_tags);

CREATE INDEX IF NOT EXISTS problems_fts_idx
    ON problems USING GIN (fts_vector);

-- ── Full-text search trigger ──────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_problems_fts()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.fts_vector := to_tsvector('hungarian', COALESCE(NEW.statement_text, ''));
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER problems_fts_trigger
    BEFORE INSERT OR UPDATE OF statement_text
    ON problems
    FOR EACH ROW EXECUTE FUNCTION update_problems_fts();

-- ── Row-Level Security ────────────────────────────────────────────────────────

ALTER TABLE problems ENABLE ROW LEVEL SECURITY;

-- Anonymous and authenticated users can only read approved problems
DO $$ BEGIN
    CREATE POLICY "Public read reviewed problems"
        ON problems FOR SELECT
        TO anon, authenticated
        USING (human_reviewed = true);
EXCEPTION WHEN duplicate_object THEN NULL;
END; $$;

-- service_role bypasses RLS by default in Supabase — no explicit policy needed
-- (used by the import script and the review app)
