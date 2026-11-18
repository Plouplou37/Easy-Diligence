-- Migration: Add validator_id column to dd_executions table
-- Date: 2025-08-26
-- Description: Fix database schema mismatch where DDExecution model expects validator_id column

-- Add validator_id column to dd_executions table
ALTER TABLE dd_executions 
ADD COLUMN IF NOT EXISTS validator_id INTEGER REFERENCES users(id);

-- Add comment for documentation
COMMENT ON COLUMN dd_executions.validator_id IS 'ID of the user assigned to validate this execution';