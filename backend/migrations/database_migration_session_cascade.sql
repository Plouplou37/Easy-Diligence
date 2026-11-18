-- Database Migration: Add CASCADE DELETE to session foreign keys
-- This allows automatic deletion of related records when a session is deleted
--
-- WARNING: This will modify existing foreign key constraints
-- Backup your database before running this migration!

-- Step 1: Find existing constraint names (run these queries first to get actual constraint names)
-- SELECT CONSTRAINT_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME = 'dd_answers'
--   AND COLUMN_NAME = 'session_id';

-- SELECT CONSTRAINT_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME = 'session_vector_stores'
--   AND COLUMN_NAME = 'session_id';

-- Step 2: Drop and recreate foreign keys with CASCADE delete
-- Replace 'dd_answers_ibfk_1' with the actual constraint name from Step 1 if different

-- Modify dd_answers.session_id foreign key
ALTER TABLE dd_answers
DROP FOREIGN KEY dd_answers_ibfk_1;

ALTER TABLE dd_answers
ADD CONSTRAINT dd_answers_ibfk_1
FOREIGN KEY (session_id)
REFERENCES dd_sessions(id)
ON DELETE CASCADE;

-- Modify session_vector_stores.session_id foreign key
ALTER TABLE session_vector_stores
DROP FOREIGN KEY session_vector_stores_ibfk_1;

ALTER TABLE session_vector_stores
ADD CONSTRAINT session_vector_stores_ibfk_1
FOREIGN KEY (session_id)
REFERENCES dd_sessions(id)
ON DELETE CASCADE;

-- Step 3: Verify the changes
-- Run these to confirm CASCADE is now enabled:
-- SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, DELETE_RULE
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE k
-- JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS r
--   ON k.CONSTRAINT_NAME = r.CONSTRAINT_NAME
-- WHERE k.TABLE_SCHEMA = DATABASE()
--   AND k.COLUMN_NAME = 'session_id'
--   AND k.TABLE_NAME IN ('dd_answers', 'session_vector_stores');
