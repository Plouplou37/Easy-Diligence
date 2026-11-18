-- Migration: Add name column to vector_stores table
-- Date: 2025-08-26
-- Description: Fix database schema mismatch where VectorStore model expects name column

-- Add name column to vector_stores table
ALTER TABLE vector_stores 
ADD COLUMN IF NOT EXISTS name VARCHAR(255);

-- Set default name for existing records (if any)
UPDATE vector_stores 
SET name = CONCAT('Vector Store ', id) 
WHERE name IS NULL OR name = '';

-- Make name column NOT NULL after setting defaults
ALTER TABLE vector_stores 
ALTER COLUMN name SET NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN vector_stores.name IS 'Human-readable name for the vector store';