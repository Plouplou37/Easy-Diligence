-- Migration 012: Create Independent Vector Store Management System
-- This migration introduces independent vector store management with expiration policies
-- and flexible session/DD type assignments
-- Date: 2025-08-18

BEGIN;

-- Create vector_stores table for independent vector store management
CREATE TABLE vector_stores (
    id VARCHAR(255) PRIMARY KEY,              -- OpenAI vector store ID
    name VARCHAR(255) NOT NULL,               -- User-friendly name
    description TEXT,                         -- User description
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_after_days INTEGER,               -- Expiration policy in days
    expires_at TIMESTAMP WITH TIME ZONE,      -- Calculated expiration date
    last_active_at TIMESTAMP WITH TIME ZONE,  -- Last used timestamp
    file_count INTEGER DEFAULT 0,             -- Number of files
    total_size_bytes BIGINT DEFAULT 0,        -- Total storage used in bytes
    status VARCHAR(50) DEFAULT 'active',      -- active, expired, deleted
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create junction table for flexible session/DD type vector store assignments
CREATE TABLE session_vector_stores (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES dd_sessions(id) ON DELETE CASCADE,
    dd_type_code VARCHAR(50),                 -- NULL = whole session, specific code = DD type only
    vector_store_id VARCHAR(255) NOT NULL REFERENCES vector_stores(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicate assignments
    UNIQUE(session_id, dd_type_code)
);

-- Add indexes for performance
CREATE INDEX idx_vector_stores_created_by ON vector_stores(created_by);
CREATE INDEX idx_vector_stores_status ON vector_stores(status);
CREATE INDEX idx_vector_stores_expires_at ON vector_stores(expires_at);
CREATE INDEX idx_session_vector_stores_session ON session_vector_stores(session_id);
CREATE INDEX idx_session_vector_stores_vector_store ON session_vector_stores(vector_store_id);

-- Add foreign key constraint to documents table for vector store reference
ALTER TABLE documents 
ADD CONSTRAINT fk_documents_vector_store 
FOREIGN KEY (vector_store_id) REFERENCES vector_stores(id) ON DELETE SET NULL;

-- Add openai_file_id column to documents for better file management
ALTER TABLE documents ADD COLUMN openai_file_id VARCHAR(255);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_vector_stores_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_vector_stores_updated_at
    BEFORE UPDATE ON vector_stores
    FOR EACH ROW
    EXECUTE FUNCTION update_vector_stores_updated_at();

-- Add check constraints for data integrity
ALTER TABLE vector_stores ADD CONSTRAINT check_expires_after_days_positive 
CHECK (expires_after_days IS NULL OR expires_after_days > 0);

ALTER TABLE vector_stores ADD CONSTRAINT check_file_count_non_negative 
CHECK (file_count >= 0);

ALTER TABLE vector_stores ADD CONSTRAINT check_total_size_non_negative 
CHECK (total_size_bytes >= 0);

ALTER TABLE vector_stores ADD CONSTRAINT check_valid_status 
CHECK (status IN ('active', 'expired', 'deleted'));

-- Add constraint for dd_type_code reference (if not NULL, must be valid)
ALTER TABLE session_vector_stores 
ADD CONSTRAINT fk_session_vector_stores_dd_type 
FOREIGN KEY (dd_type_code) REFERENCES dd_types(code) ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMIT;

-- Verification queries (run these manually after migration)
/*
-- Verify tables were created correctly
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name IN ('vector_stores', 'session_vector_stores')
ORDER BY table_name, ordinal_position;

-- Verify indexes were created
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('vector_stores', 'session_vector_stores');

-- Verify constraints were added
SELECT conname, contype, conrelid::regclass 
FROM pg_constraint 
WHERE conrelid::regclass::text IN ('vector_stores', 'session_vector_stores');
*/