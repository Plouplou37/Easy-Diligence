-- Migration 018: Phase 3 Critical Bug Fixes
-- Add missing enum values and company audit fields
-- Addresses issues found in FLOW_ANALYSIS_REPORT.md

BEGIN;

-- 1. Add new enum values to answerstatus
-- The enum crisis was caused by missing 'draft', 'under_review', 'validated', 'needs_revision' values
ALTER TYPE answerstatus ADD VALUE IF NOT EXISTS 'draft';
ALTER TYPE answerstatus ADD VALUE IF NOT EXISTS 'under_review';  
ALTER TYPE answerstatus ADD VALUE IF NOT EXISTS 'validated';
ALTER TYPE answerstatus ADD VALUE IF NOT EXISTS 'needs_revision';

-- 2. Add updated_by column to companies table (for audit trail)
-- This was missing from the Company model implementation
ALTER TABLE companies ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);

-- 3. Create index on updated_by for performance
CREATE INDEX IF NOT EXISTS idx_companies_updated_by ON companies(updated_by);

-- 4. Update any existing companies to set updated_by same as created_by (data consistency)
UPDATE companies 
SET updated_by = created_by 
WHERE updated_by IS NULL AND created_by IS NOT NULL;

-- 5. Record migration completion
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version) VALUES ('018_phase3_critical_fixes')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- Verification queries (run these to check migration success):
-- SELECT unnest(enum_range(NULL::answerstatus)) AS answerstatus_values;
-- SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'companies' AND column_name = 'updated_by';
-- SELECT COUNT(*) as companies_with_updated_by FROM companies WHERE updated_by IS NOT NULL;