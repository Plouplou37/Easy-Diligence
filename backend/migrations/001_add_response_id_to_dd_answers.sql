-- ISSUE #7 FIX: Add response_id column to dd_answers table
-- This enables proper context chain tracking when retrying failed questions
--
-- Migration: 001_add_response_id_to_dd_answers
-- Date: 2025-10-03
-- Description: Add response_id foreign key to track which OpenAI response generated each answer

-- Add response_id column
ALTER TABLE dd_answers
ADD COLUMN response_id VARCHAR(255) NULL;

-- Add foreign key constraint
ALTER TABLE dd_answers
ADD CONSTRAINT fk_dd_answers_response_id
FOREIGN KEY (response_id) REFERENCES dd_responses(response_id)
ON DELETE SET NULL;

-- Add index for better query performance
CREATE INDEX idx_dd_answers_response_id ON dd_answers(response_id);

-- Rollback instructions (if needed):
-- DROP INDEX idx_dd_answers_response_id;
-- ALTER TABLE dd_answers DROP FOREIGN KEY fk_dd_answers_response_id;
-- ALTER TABLE dd_answers DROP COLUMN response_id;
