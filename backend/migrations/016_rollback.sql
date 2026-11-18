-- Rollback Script for Migration 016: Answer Management System
-- Created: 2025-08-22
-- WARNING: This rollback will DROP TABLES and DATA. Use with extreme caution!
-- IMPORTANT: Take a backup before running this rollback script

BEGIN;

-- Confirmation check
DO $$
BEGIN
    RAISE NOTICE '⚠️  WARNING: This rollback will permanently delete all answer management system data!';
    RAISE NOTICE '⚠️  Tables to be dropped: dd_executions, dd_responses, dd_messages, dd_answer_history, dd_answer_validations, session_dd_types';
    RAISE NOTICE '⚠️  Columns to be removed from dd_answers: execution_id, version, is_current, status, edited_by, edited_at';
    RAISE NOTICE '⚠️  Make sure you have a backup before proceeding!';
    RAISE NOTICE '🔄 Starting rollback in 3 seconds...';
    
    -- Small delay to allow reading the warnings
    PERFORM pg_sleep(3);
END $$;

-- Phase 1: Drop triggers first
DROP TRIGGER IF EXISTS update_dd_executions_updated_at ON dd_executions;
DROP TRIGGER IF EXISTS update_dd_answer_validations_updated_at ON dd_answer_validations;
DROP FUNCTION IF EXISTS update_updated_at_column();
RAISE NOTICE '✓ Dropped triggers and functions';

-- Phase 2: Drop indexes (they will be auto-dropped with tables, but explicit for clarity)
DROP INDEX IF EXISTS idx_dd_executions_session_dd_type;
DROP INDEX IF EXISTS idx_dd_executions_status;
DROP INDEX IF EXISTS idx_dd_executions_conversation;
DROP INDEX IF EXISTS idx_dd_responses_execution;
DROP INDEX IF EXISTS idx_dd_responses_conversation;
DROP INDEX IF EXISTS idx_dd_responses_response_id;
DROP INDEX IF EXISTS idx_dd_messages_response;
DROP INDEX IF EXISTS idx_dd_messages_role;
DROP INDEX IF EXISTS idx_dd_answers_execution;
DROP INDEX IF EXISTS idx_dd_answers_current;
DROP INDEX IF EXISTS idx_dd_answers_status;
DROP INDEX IF EXISTS idx_dd_answer_history_answer;
DROP INDEX IF EXISTS idx_dd_answer_history_editor;
DROP INDEX IF EXISTS idx_dd_answer_validations_answer;
DROP INDEX IF EXISTS idx_dd_answer_validations_validator;
DROP INDEX IF EXISTS idx_dd_answer_validations_status;
DROP INDEX IF EXISTS idx_session_dd_types_session;
DROP INDEX IF EXISTS idx_session_dd_types_status;
RAISE NOTICE '✓ Dropped indexes';

-- Phase 3: Drop foreign key constraints on dd_answers table
DO $$
BEGIN
    -- Drop execution_id foreign key
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = 'fk_answer_execution' AND table_name = 'dd_answers') THEN
        ALTER TABLE dd_answers DROP CONSTRAINT fk_answer_execution;
        RAISE NOTICE '✓ Dropped fk_answer_execution constraint';
    END IF;
    
    -- Drop edited_by foreign key
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = 'fk_answer_editor' AND table_name = 'dd_answers') THEN
        ALTER TABLE dd_answers DROP CONSTRAINT fk_answer_editor;
        RAISE NOTICE '✓ Dropped fk_answer_editor constraint';
    END IF;
END $$;

-- Phase 4: Drop tables in dependency order (children first)
DROP TABLE IF EXISTS dd_answer_validations CASCADE;
RAISE NOTICE '✓ Dropped dd_answer_validations table';

DROP TABLE IF EXISTS dd_answer_history CASCADE;
RAISE NOTICE '✓ Dropped dd_answer_history table';

DROP TABLE IF EXISTS session_dd_types CASCADE;
RAISE NOTICE '✓ Dropped session_dd_types table';

DROP TABLE IF EXISTS dd_messages CASCADE;
RAISE NOTICE '✓ Dropped dd_messages table';

DROP TABLE IF EXISTS dd_responses CASCADE;
RAISE NOTICE '✓ Dropped dd_responses table';

DROP TABLE IF EXISTS dd_executions CASCADE;
RAISE NOTICE '✓ Dropped dd_executions table';

-- Phase 5: Remove columns from dd_answers table
DO $$
BEGIN
    -- Remove edited_at column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'edited_at') THEN
        ALTER TABLE dd_answers DROP COLUMN edited_at;
        RAISE NOTICE '✓ Removed edited_at column from dd_answers';
    END IF;
    
    -- Remove edited_by column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'edited_by') THEN
        ALTER TABLE dd_answers DROP COLUMN edited_by;
        RAISE NOTICE '✓ Removed edited_by column from dd_answers';
    END IF;
    
    -- Remove status column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'status') THEN
        ALTER TABLE dd_answers DROP COLUMN status;
        RAISE NOTICE '✓ Removed status column from dd_answers';
    END IF;
    
    -- Remove is_current column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'is_current') THEN
        ALTER TABLE dd_answers DROP COLUMN is_current;
        RAISE NOTICE '✓ Removed is_current column from dd_answers';
    END IF;
    
    -- Remove version column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'version') THEN
        ALTER TABLE dd_answers DROP COLUMN version;
        RAISE NOTICE '✓ Removed version column from dd_answers';
    END IF;
    
    -- Remove execution_id column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'execution_id') THEN
        ALTER TABLE dd_answers DROP COLUMN execution_id;
        RAISE NOTICE '✓ Removed execution_id column from dd_answers';
    END IF;
END $$;

-- Phase 6: Drop enum types (only if no other tables use them)
DO $$
BEGIN
    -- Check and drop SessionDDTypeStatus
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sessionddtypestatus') THEN
        DROP TYPE SessionDDTypeStatus;
        RAISE NOTICE '✓ Dropped SessionDDTypeStatus enum type';
    END IF;
EXCEPTION
    WHEN dependent_objects_still_exist THEN
        RAISE NOTICE '⚠️  Cannot drop SessionDDTypeStatus enum - other objects depend on it';
END $$;

DO $$
BEGIN
    -- Check and drop ValidationStatus
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'validationstatus') THEN
        DROP TYPE ValidationStatus;
        RAISE NOTICE '✓ Dropped ValidationStatus enum type';
    END IF;
EXCEPTION
    WHEN dependent_objects_still_exist THEN
        RAISE NOTICE '⚠️  Cannot drop ValidationStatus enum - other objects depend on it';
END $$;

DO $$
BEGIN
    -- Check and drop AnswerStatus
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'answerstatus') THEN
        DROP TYPE AnswerStatus;
        RAISE NOTICE '✓ Dropped AnswerStatus enum type';
    END IF;
EXCEPTION
    WHEN dependent_objects_still_exist THEN
        RAISE NOTICE '⚠️  Cannot drop AnswerStatus enum - other objects depend on it';
END $$;

DO $$
BEGIN
    -- Check and drop ExecutionStatus
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executionstatus') THEN
        DROP TYPE ExecutionStatus;
        RAISE NOTICE '✓ Dropped ExecutionStatus enum type';
    END IF;
EXCEPTION
    WHEN dependent_objects_still_exist THEN
        RAISE NOTICE '⚠️  Cannot drop ExecutionStatus enum - other objects depend on it';
END $$;

-- Phase 7: Remove migration record
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations') THEN
        DELETE FROM schema_migrations WHERE version = '016_answer_management_system';
        RAISE NOTICE '✓ Removed migration record from schema_migrations';
    END IF;
END $$;

RAISE NOTICE '';
RAISE NOTICE '🔄 Rollback completed successfully!';
RAISE NOTICE '✓ All answer management system tables and columns have been removed';
RAISE NOTICE '✓ Database schema reverted to pre-migration state';
RAISE NOTICE '⚠️  Remember to restart your application to reload schema changes';
RAISE NOTICE '';

COMMIT;