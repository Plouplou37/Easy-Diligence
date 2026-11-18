-- Migration 013: Remove legacy fields from answer and progress tables
-- This migration removes deprecated columns that have been replaced by proper foreign key relationships

-- Remove legacy fields from dd_answers table
ALTER TABLE dd_answers 
DROP COLUMN IF EXISTS dd_type,
DROP COLUMN IF EXISTS section_code,
DROP COLUMN IF EXISTS question_code;

-- Remove legacy fields from dd_progress table  
ALTER TABLE dd_progress
DROP COLUMN IF EXISTS dd_type;

-- Remove legacy vector_store_ids field from dd_sessions table
-- (This field is now replaced by the session_vector_stores table)
ALTER TABLE dd_sessions
DROP COLUMN IF EXISTS vector_store_ids;

-- Note: This migration removes legacy functionality that has been replaced
-- by proper foreign key relationships in the new vector store assignment system