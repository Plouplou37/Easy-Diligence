-- Migration 015: Add missing openai_file_id column to documents table
-- This column is referenced in the Document model but was never added to the database

ALTER TABLE documents ADD COLUMN openai_file_id VARCHAR(255);

-- Add comment for documentation
COMMENT ON COLUMN documents.openai_file_id IS 'OpenAI file ID for deletion and tracking';

-- Create index for better performance when looking up files by OpenAI ID
CREATE INDEX idx_documents_openai_file_id ON documents(openai_file_id);