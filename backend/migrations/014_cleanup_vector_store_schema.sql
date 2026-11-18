-- Migration 014: Cleanup Vector Store Schema - Use OpenAI as Single Source of Truth
-- This migration removes redundant fields that are now fetched from OpenAI API
-- Date: 2025-08-19

BEGIN;

-- Drop indexes that reference columns we're removing
DROP INDEX IF EXISTS idx_vector_stores_status;
DROP INDEX IF EXISTS idx_vector_stores_expires_at;

-- Drop check constraints that reference columns we're removing
ALTER TABLE vector_stores DROP CONSTRAINT IF EXISTS check_expires_after_days_positive;
ALTER TABLE vector_stores DROP CONSTRAINT IF EXISTS check_file_count_non_negative;
ALTER TABLE vector_stores DROP CONSTRAINT IF EXISTS check_total_size_non_negative;
ALTER TABLE vector_stores DROP CONSTRAINT IF EXISTS check_valid_status;

-- Remove redundant columns (OpenAI is now single source of truth for these)
ALTER TABLE vector_stores DROP COLUMN IF EXISTS name;                -- Get from OpenAI
ALTER TABLE vector_stores DROP COLUMN IF EXISTS expires_after_days;  -- Get from OpenAI  
ALTER TABLE vector_stores DROP COLUMN IF EXISTS expires_at;          -- Get from OpenAI
ALTER TABLE vector_stores DROP COLUMN IF EXISTS last_active_at;      -- Get from OpenAI
ALTER TABLE vector_stores DROP COLUMN IF EXISTS file_count;          -- Get from OpenAI
ALTER TABLE vector_stores DROP COLUMN IF EXISTS total_size_bytes;    -- Get from OpenAI
ALTER TABLE vector_stores DROP COLUMN IF EXISTS status;              -- Get from OpenAI

-- Keep only essential tracking fields:
-- id (OpenAI vector store ID - primary key)
-- description (our custom field, not stored in OpenAI)
-- created_by (our ownership tracking)
-- created_at (our record creation tracking)
-- updated_at (our record modification tracking)

-- Add comment to document the new approach
COMMENT ON TABLE vector_stores IS 'Minimal tracking table for vector stores - metadata fetched from OpenAI API';
COMMENT ON COLUMN vector_stores.id IS 'OpenAI vector store ID (primary key)';
COMMENT ON COLUMN vector_stores.description IS 'User-provided description (not stored in OpenAI)';
COMMENT ON COLUMN vector_stores.created_by IS 'User who created this vector store';
COMMENT ON COLUMN vector_stores.created_at IS 'When this record was created in our system';
COMMENT ON COLUMN vector_stores.updated_at IS 'When this record was last updated in our system';

COMMIT;

-- Verification queries (run these manually after migration)
/*
-- Verify the cleaned up schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'vector_stores'
ORDER BY ordinal_position;

-- Verify remaining indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename = 'vector_stores';

-- Verify remaining constraints
SELECT conname, contype, conrelid::regclass 
FROM pg_constraint 
WHERE conrelid::regclass::text = 'vector_stores';
*/