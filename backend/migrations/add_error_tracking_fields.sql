-- Migration: Add error tracking fields to dd_answers table
-- Date: 2025-10-02

-- Add error_type enum column
ALTER TABLE dd_answers
ADD COLUMN error_type ENUM(
    'rate_limit',
    'context_overflow',
    'api_error',
    'network_error',
    'validation_error',
    'timeout',
    'unknown'
) NULL AFTER retry_count;

-- Add error_message column
ALTER TABLE dd_answers
ADD COLUMN error_message TEXT NULL AFTER error_type;

-- Add last_error_at column
ALTER TABLE dd_answers
ADD COLUMN last_error_at DATETIME NULL AFTER error_message;

-- Add index on error_type for faster querying of failed answers
CREATE INDEX idx_dd_answers_error_type ON dd_answers(error_type);

-- Add index on last_error_at for error tracking queries
CREATE INDEX idx_dd_answers_last_error_at ON dd_answers(last_error_at);
