-- Migration: Add updated_at to coverage_courses
-- Issue: Opus audit found coverage_courses UPDATE sets updated_at but column doesn't exist

ALTER TABLE coverage_courses
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_coverage_courses_updated_at ON coverage_courses;

CREATE TRIGGER update_coverage_courses_updated_at
    BEFORE UPDATE ON coverage_courses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
