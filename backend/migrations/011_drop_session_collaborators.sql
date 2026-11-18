-- Migration 011: Drop unused session_collaborators table
-- This migration removes the unused collaboration system to simplify the schema
-- Date: 2025-08-18

BEGIN;

-- Drop the unused session_collaborators table
-- This table was defined in models but never used in any APIs or business logic
DROP TABLE IF EXISTS session_collaborators;

-- Drop any associated sequence that might exist
DROP SEQUENCE IF EXISTS session_collaborators_id_seq;

-- Verification: Ensure the table no longer exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'session_collaborators') THEN
        RAISE EXCEPTION 'Failed to drop session_collaborators table';
    ELSE
        RAISE NOTICE 'session_collaborators table successfully removed';
    END IF;
END $$;

COMMIT;

-- Note: This migration removes unused functionality that was never implemented
-- The current creator/assignee access control model in dd_sessions remains intact
-- and provides sufficient access control for the application