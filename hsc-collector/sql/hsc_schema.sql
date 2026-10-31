CREATE TABLE IF NOT EXISTS public.hsc_institutions (
    eiin TEXT PRIMARY KEY,
    institution_name TEXT NOT NULL,
    district TEXT,
    thana TEXT,
    appeared INTEGER NOT NULL DEFAULT 0,
    passed INTEGER NOT NULL DEFAULT 0,
    passing_rate NUMERIC(6,2) NOT NULL DEFAULT 0,
    gpa5 INTEGER NOT NULL DEFAULT 0,
    total_gpa NUMERIC,
    year INTEGER NOT NULL DEFAULT 2026,
    board TEXT NOT NULL DEFAULT 'Chattogram Board',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT hsc_appeared_nonnegative CHECK (appeared >= 0),
    CONSTRAINT hsc_passed_nonnegative CHECK (passed >= 0),
    CONSTRAINT hsc_gpa5_nonnegative CHECK (gpa5 >= 0),
    CONSTRAINT hsc_passed_limit CHECK (passed <= appeared),
    CONSTRAINT hsc_gpa5_limit CHECK (gpa5 <= passed),
    CONSTRAINT hsc_passing_rate_limit CHECK (
        passing_rate >= 0 AND passing_rate <= 100
    )
);

CREATE INDEX IF NOT EXISTS idx_hsc_institutions_district
ON public.hsc_institutions (district);

CREATE INDEX IF NOT EXISTS idx_hsc_institutions_thana
ON public.hsc_institutions (thana);

CREATE INDEX IF NOT EXISTS idx_hsc_institutions_year
ON public.hsc_institutions (year);
