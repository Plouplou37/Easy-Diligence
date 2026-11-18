-- Migration 016: Answer Management System
-- Created: 2025-08-22
-- Description: Add complete answer management system with execution workflow, 
--              version control, and validation system

BEGIN;

-- Safety check: Verify prerequisites exist
DO $$
BEGIN
    -- Check required tables exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dd_sessions') THEN
        RAISE EXCEPTION 'Missing prerequisite table: dd_sessions. Please ensure all previous migrations are applied.';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dd_types') THEN
        RAISE EXCEPTION 'Missing prerequisite table: dd_types. Please ensure all previous migrations are applied.';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dd_answers') THEN
        RAISE EXCEPTION 'Missing prerequisite table: dd_answers. Please ensure all previous migrations are applied.';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        RAISE EXCEPTION 'Missing prerequisite table: users. Please ensure all previous migrations are applied.';
    END IF;
    
    RAISE NOTICE 'Prerequisites verified. Proceeding with migration...';
END $$;

-- Phase 1: Create enum types for status management
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executionstatus') THEN
        CREATE TYPE ExecutionStatus AS ENUM ('not_started', 'in_progress', 'generated', 'under_review', 'validated', 'finalized');
        RAISE NOTICE 'Created ExecutionStatus enum type';
    ELSE
        RAISE NOTICE 'ExecutionStatus enum type already exists, skipping';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'answerstatus') THEN
        CREATE TYPE AnswerStatus AS ENUM ('draft', 'under_review', 'validated', 'archived');
        RAISE NOTICE 'Created AnswerStatus enum type';
    ELSE
        RAISE NOTICE 'AnswerStatus enum type already exists, skipping';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'validationstatus') THEN
        CREATE TYPE ValidationStatus AS ENUM ('approved', 'rejected', 'needs_revision');
        RAISE NOTICE 'Created ValidationStatus enum type';
    ELSE
        RAISE NOTICE 'ValidationStatus enum type already exists, skipping';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sessionddtypestatus') THEN
        CREATE TYPE SessionDDTypeStatus AS ENUM ('pending', 'in_progress', 'completed', 'skipped');
        RAISE NOTICE 'Created SessionDDTypeStatus enum type';
    ELSE
        RAISE NOTICE 'SessionDDTypeStatus enum type already exists, skipping';
    END IF;
END $$;

-- Phase 2: Create dd_executions table for workflow tracking
CREATE TABLE IF NOT EXISTS dd_executions (
    id SERIAL PRIMARY KEY,
    session_id INT NOT NULL,
    dd_type_code VARCHAR(50) NOT NULL,
    status ExecutionStatus DEFAULT 'not_started',
    conversation_id VARCHAR(255) UNIQUE,
    validated_at TIMESTAMP,
    validated_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_execution_session FOREIGN KEY (session_id) REFERENCES dd_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_execution_dd_type FOREIGN KEY (dd_type_code) REFERENCES dd_types(code) ON DELETE RESTRICT,
    CONSTRAINT fk_execution_validator FOREIGN KEY (validated_by) REFERENCES users(id),
    
    -- Business logic constraints
    CONSTRAINT unique_session_dd_type_active UNIQUE (session_id, dd_type_code)
);

RAISE NOTICE 'Created dd_executions table';

-- Phase 3: Create dd_responses table for OpenAI API response tracking
CREATE TABLE IF NOT EXISTS dd_responses (
    id SERIAL PRIMARY KEY,
    execution_id INT NOT NULL,
    response_id VARCHAR(255) NOT NULL UNIQUE,
    previous_response_id VARCHAR(255),
    openai_response JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_response_execution FOREIGN KEY (execution_id) REFERENCES dd_executions(id) ON DELETE CASCADE,
    CONSTRAINT fk_response_previous FOREIGN KEY (previous_response_id) REFERENCES dd_responses(response_id)
);

RAISE NOTICE 'Created dd_responses table';

-- Phase 4: Create dd_messages table for message extraction from responses
CREATE TABLE IF NOT EXISTS dd_messages (
    id SERIAL PRIMARY KEY,
    response_id VARCHAR(255) NOT NULL,
    message_index INT NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT,
    tool_calls JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_message_response FOREIGN KEY (response_id) REFERENCES dd_responses(response_id) ON DELETE CASCADE,
    
    -- Business logic constraints
    CONSTRAINT unique_response_message UNIQUE(response_id, message_index),
    CONSTRAINT valid_role CHECK (role IN ('system', 'user', 'assistant', 'tool'))
);

RAISE NOTICE 'Created dd_messages table';

-- Phase 5: Update dd_answers table with version control and execution linking
DO $$
BEGIN
    -- Add execution_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'execution_id') THEN
        ALTER TABLE dd_answers ADD COLUMN execution_id INT;
        ALTER TABLE dd_answers ADD CONSTRAINT fk_answer_execution FOREIGN KEY (execution_id) REFERENCES dd_executions(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added execution_id column to dd_answers';
    ELSE
        RAISE NOTICE 'execution_id column already exists in dd_answers';
    END IF;
    
    -- Add version column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'version') THEN
        ALTER TABLE dd_answers ADD COLUMN version INT DEFAULT 1;
        RAISE NOTICE 'Added version column to dd_answers';
    ELSE
        RAISE NOTICE 'version column already exists in dd_answers';
    END IF;
    
    -- Add is_current column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'is_current') THEN
        ALTER TABLE dd_answers ADD COLUMN is_current BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added is_current column to dd_answers';
    ELSE
        RAISE NOTICE 'is_current column already exists in dd_answers';
    END IF;
    
    -- Add status column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'status') THEN
        ALTER TABLE dd_answers ADD COLUMN status AnswerStatus DEFAULT 'draft';
        RAISE NOTICE 'Added status column to dd_answers';
    ELSE
        RAISE NOTICE 'status column already exists in dd_answers';
    END IF;
    
    -- Add edited_by column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'edited_by') THEN
        ALTER TABLE dd_answers ADD COLUMN edited_by INT;
        ALTER TABLE dd_answers ADD CONSTRAINT fk_answer_editor FOREIGN KEY (edited_by) REFERENCES users(id);
        RAISE NOTICE 'Added edited_by column to dd_answers';
    ELSE
        RAISE NOTICE 'edited_by column already exists in dd_answers';
    END IF;
    
    -- Add edited_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'dd_answers' AND column_name = 'edited_at') THEN
        ALTER TABLE dd_answers ADD COLUMN edited_at TIMESTAMP;
        RAISE NOTICE 'Added edited_at column to dd_answers';
    ELSE
        RAISE NOTICE 'edited_at column already exists in dd_answers';
    END IF;
END $$;

-- Phase 6: Create dd_answer_history table for version tracking
CREATE TABLE IF NOT EXISTS dd_answer_history (
    id SERIAL PRIMARY KEY,
    answer_id INT NOT NULL,
    version INT NOT NULL,
    content TEXT,
    sources JSONB,
    edit_reason TEXT,
    edited_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_history_answer FOREIGN KEY (answer_id) REFERENCES dd_answers(id) ON DELETE CASCADE,
    CONSTRAINT fk_history_editor FOREIGN KEY (edited_by) REFERENCES users(id),
    
    -- Business logic constraints
    CONSTRAINT unique_answer_version UNIQUE (answer_id, version)
);

RAISE NOTICE 'Created dd_answer_history table';

-- Phase 7: Create dd_answer_validations table for validation workflow
CREATE TABLE IF NOT EXISTS dd_answer_validations (
    id SERIAL PRIMARY KEY,
    answer_id INT NOT NULL,
    validator_id INT NOT NULL,
    validation_status ValidationStatus NOT NULL,
    comments TEXT,
    validation_type VARCHAR(50) DEFAULT 'review',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_validation_answer FOREIGN KEY (answer_id) REFERENCES dd_answers(id) ON DELETE CASCADE,
    CONSTRAINT fk_validation_validator FOREIGN KEY (validator_id) REFERENCES users(id),
    
    -- Business logic constraints
    CONSTRAINT valid_validation_type CHECK (validation_type IN ('review', 'quality_check', 'final_approval'))
);

RAISE NOTICE 'Created dd_answer_validations table';

-- Phase 8: Create session_dd_types junction table
CREATE TABLE IF NOT EXISTS session_dd_types (
    id SERIAL PRIMARY KEY,
    session_id INT NOT NULL,
    dd_type_code VARCHAR(50) NOT NULL,
    execution_order INT,
    status SessionDDTypeStatus DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_session_dd_type_session FOREIGN KEY (session_id) REFERENCES dd_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_session_dd_type_dd_type FOREIGN KEY (dd_type_code) REFERENCES dd_types(code) ON DELETE RESTRICT,
    
    -- Business logic constraints
    CONSTRAINT unique_session_dd_type UNIQUE(session_id, dd_type_code)
);

RAISE NOTICE 'Created session_dd_types table';

-- Phase 9: Create performance indexes
-- Execution indexes
CREATE INDEX IF NOT EXISTS idx_dd_executions_session_dd_type ON dd_executions(session_id, dd_type_code);
CREATE INDEX IF NOT EXISTS idx_dd_executions_status ON dd_executions(status);
CREATE INDEX IF NOT EXISTS idx_dd_executions_conversation ON dd_executions(conversation_id);

-- Response indexes  
CREATE INDEX IF NOT EXISTS idx_dd_responses_execution ON dd_responses(execution_id);
CREATE INDEX IF NOT EXISTS idx_dd_responses_conversation ON dd_responses(previous_response_id);
CREATE INDEX IF NOT EXISTS idx_dd_responses_response_id ON dd_responses(response_id);

-- Message indexes
CREATE INDEX IF NOT EXISTS idx_dd_messages_response ON dd_messages(response_id);
CREATE INDEX IF NOT EXISTS idx_dd_messages_role ON dd_messages(response_id, role);

-- Answer indexes
CREATE INDEX IF NOT EXISTS idx_dd_answers_execution ON dd_answers(execution_id);
CREATE INDEX IF NOT EXISTS idx_dd_answers_current ON dd_answers(execution_id, is_current) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_dd_answers_status ON dd_answers(status);

-- History indexes
CREATE INDEX IF NOT EXISTS idx_dd_answer_history_answer ON dd_answer_history(answer_id, version);
CREATE INDEX IF NOT EXISTS idx_dd_answer_history_editor ON dd_answer_history(edited_by);

-- Validation indexes
CREATE INDEX IF NOT EXISTS idx_dd_answer_validations_answer ON dd_answer_validations(answer_id);
CREATE INDEX IF NOT EXISTS idx_dd_answer_validations_validator ON dd_answer_validations(validator_id);
CREATE INDEX IF NOT EXISTS idx_dd_answer_validations_status ON dd_answer_validations(validation_status);

-- Session DD type indexes
CREATE INDEX IF NOT EXISTS idx_session_dd_types_session ON session_dd_types(session_id);
CREATE INDEX IF NOT EXISTS idx_session_dd_types_status ON session_dd_types(status);

RAISE NOTICE 'Created performance indexes';

-- Phase 10: Add updated_at trigger for dd_executions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_dd_executions_updated_at ON dd_executions;
CREATE TRIGGER update_dd_executions_updated_at 
    BEFORE UPDATE ON dd_executions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_dd_answer_validations_updated_at ON dd_answer_validations;
CREATE TRIGGER update_dd_answer_validations_updated_at 
    BEFORE UPDATE ON dd_answer_validations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

RAISE NOTICE 'Created updated_at triggers';

-- Phase 11: Record migration in schema_migrations table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations') THEN
        INSERT INTO schema_migrations (version, applied_at) 
        VALUES ('016_answer_management_system', CURRENT_TIMESTAMP)
        ON CONFLICT (version) DO NOTHING;
        RAISE NOTICE 'Recorded migration in schema_migrations table';
    ELSE
        RAISE NOTICE 'schema_migrations table does not exist, skipping migration record';
    END IF;
END $$;

RAISE NOTICE 'Migration 016_answer_management_system completed successfully!';
RAISE NOTICE 'New tables: dd_executions, dd_responses, dd_messages, dd_answer_history, dd_answer_validations, session_dd_types';
RAISE NOTICE 'Modified table: dd_answers (added 6 new columns)';
RAISE NOTICE 'Created 15 performance indexes and 2 update triggers';

COMMIT;