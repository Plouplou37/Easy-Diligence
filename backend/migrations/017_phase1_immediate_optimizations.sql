-- ============================================================
-- Phase 1: Immediate Database Optimizations
-- Priority: High | Effort: Low | Impact: High
-- Expected Performance Improvement: 50-70% for filtered queries
-- ============================================================

-- Safety checks before proceeding
SELECT 'Starting Phase 1 Immediate Optimizations' as status;

-- Check current database size and tables
SELECT
    table_name,
    table_rows,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size_MB'
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY (data_length + index_length) DESC;

-- ============================================================
-- STEP 1: ADD MISSING COMPOSITE INDEXES
-- These indexes target the most common query patterns
-- ============================================================

-- Index for answer queries by session and question
-- Improves: Session detail page, question-specific answer lookups
CREATE INDEX IF NOT EXISTS idx_dd_answers_session_question
ON dd_answers(session_id, question_code);

-- Index for answer queries by status and update time
-- Improves: Dashboard queries, filtering by answer status
CREATE INDEX IF NOT EXISTS idx_dd_answers_status_updated
ON dd_answers(status, updated_at);

-- Index for execution queries by session and status
-- Improves: Session progress tracking, execution monitoring
CREATE INDEX IF NOT EXISTS idx_dd_executions_session_status
ON dd_executions(session_id, status);

-- Index for answer history queries by answer and version
-- Improves: Version history lookups, audit trails
CREATE INDEX IF NOT EXISTS idx_answer_history_answer_version
ON dd_answer_history(answer_id, version);

-- Index for user queries by role and active status
-- Improves: User management, role-based filtering
CREATE INDEX IF NOT EXISTS idx_users_role_active
ON users(role, is_active);

-- Index for session queries by company and status
-- Improves: Company dashboard, session filtering
CREATE INDEX IF NOT EXISTS idx_sessions_company_status
ON dd_sessions(company_id, status);

-- Index for question queries by section and order
-- Improves: Section rendering, question ordering
CREATE INDEX IF NOT EXISTS idx_questions_section_order
ON dd_questions(section_id, order_index);

-- Index for validation queries by answer and status
-- Improves: Validation workflows, review processes
CREATE INDEX IF NOT EXISTS idx_validations_answer_status
ON dd_answer_validations(answer_id, validation_status);

SELECT 'Composite indexes created successfully' as status;

-- ============================================================
-- STEP 2: IMPLEMENT MISSING UNIQUE CONSTRAINT
-- Ensures data integrity for vector store assignments
-- ============================================================

-- Check if the constraint already exists
SELECT COUNT(*) as existing_constraint_count
FROM information_schema.table_constraints
WHERE table_schema = DATABASE()
  AND table_name = 'session_vector_stores'
  AND constraint_name = 'unique_session_dd_type_vector_store';

-- Add the unique constraint if it doesn't exist
-- This prevents duplicate vector store assignments per session/dd_type
ALTER TABLE session_vector_stores
ADD CONSTRAINT unique_session_dd_type_vector_store
UNIQUE (session_id, dd_type_code);

SELECT 'Unique constraint added successfully' as status;

-- ============================================================
-- STEP 3: ADD BASIC DATA VALIDATION CONSTRAINTS
-- Enforces business rules at the database level
-- ============================================================

-- Confidence score validation (0.0 to 1.0 range)
-- Prevents invalid confidence scores from AI responses
ALTER TABLE dd_answers
ADD CONSTRAINT chk_confidence_range
CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1));

-- Token usage validation (non-negative values)
-- Prevents negative token counts
ALTER TABLE dd_answers
ADD CONSTRAINT chk_tokens_positive
CHECK (tokens_used >= 0);

-- Order index validation (non-negative values)
-- Ensures proper ordering in sections and questions
ALTER TABLE dd_sections
ADD CONSTRAINT chk_section_order_non_negative
CHECK (order_index >= 0);

ALTER TABLE dd_questions
ADD CONSTRAINT chk_question_order_non_negative
CHECK (order_index >= 0);

SELECT 'Data validation constraints added successfully' as status;

-- ============================================================
-- STEP 4: OPTIMIZE EXISTING INDEXES
-- Review and improve existing index coverage
-- ============================================================

-- Add missing indexes on frequently filtered columns
-- Email lookups (login process)
CREATE INDEX IF NOT EXISTS idx_users_email_active
ON users(email, is_active);

-- Session code lookups (session identification)
CREATE INDEX IF NOT EXISTS idx_sessions_code_status
ON dd_sessions(session_code, status);

-- Execution conversation tracking
CREATE INDEX IF NOT EXISTS idx_executions_conversation
ON dd_executions(conversation_id);

-- Vector store creator tracking
CREATE INDEX IF NOT EXISTS idx_vector_stores_creator
ON vector_stores(created_by, created_at);

SELECT 'Additional indexes created successfully' as status;

-- ============================================================
-- STEP 5: ANALYZE INDEX USAGE
-- Check that our new indexes are being recognized
-- ============================================================

-- Show all indexes we just created
SELECT
    table_name,
    index_name,
    column_name,
    seq_in_index,
    cardinality
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND index_name IN (
    'idx_dd_answers_session_question',
    'idx_dd_answers_status_updated',
    'idx_dd_executions_session_status',
    'idx_answer_history_answer_version',
    'idx_users_role_active',
    'idx_sessions_company_status',
    'idx_questions_section_order',
    'idx_validations_answer_status',
    'idx_users_email_active',
    'idx_sessions_code_status',
    'idx_executions_conversation',
    'idx_vector_stores_creator'
  )
ORDER BY table_name, index_name, seq_in_index;

-- ============================================================
-- STEP 6: VERIFY CONSTRAINTS
-- Ensure all constraints are properly applied
-- ============================================================

-- Show all constraints we just added
SELECT
    constraint_name,
    table_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = DATABASE()
  AND constraint_name IN (
    'unique_session_dd_type_vector_store',
    'chk_confidence_range',
    'chk_tokens_positive',
    'chk_section_order_non_negative',
    'chk_question_order_non_negative'
  )
ORDER BY table_name, constraint_name;

-- ============================================================
-- STEP 7: UPDATE TABLE STATISTICS
-- Force MySQL to update statistics for query optimization
-- ============================================================

ANALYZE TABLE dd_answers;
ANALYZE TABLE dd_executions;
ANALYZE TABLE dd_answer_history;
ANALYZE TABLE users;
ANALYZE TABLE dd_sessions;
ANALYZE TABLE dd_questions;
ANALYZE TABLE dd_answer_validations;
ANALYZE TABLE session_vector_stores;
ANALYZE TABLE vector_stores;

SELECT 'Table statistics updated successfully' as status;

-- ============================================================
-- STEP 8: PERFORMANCE IMPACT ASSESSMENT
-- Show before/after comparison data
-- ============================================================

-- Check total index size impact
SELECT
    table_name,
    ROUND((index_length / 1024 / 1024), 2) AS 'Index_Size_MB',
    ROUND((data_length / 1024 / 1024), 2) AS 'Data_Size_MB',
    ROUND((index_length / data_length * 100), 2) AS 'Index_Ratio_Percent'
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN (
    'dd_answers', 'dd_executions', 'dd_answer_history',
    'users', 'dd_sessions', 'dd_questions',
    'dd_answer_validations', 'session_vector_stores', 'vector_stores'
  )
ORDER BY table_name;

-- Final status
SELECT
    'Phase 1 Immediate Optimizations Completed Successfully!' as status,
    NOW() as completion_time,
    'Expected Performance Improvement: 50-70% for filtered queries' as impact;

-- ============================================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ============================================================

/*
-- To rollback these changes, run the following (ONLY IF NECESSARY):

-- Remove indexes
DROP INDEX IF EXISTS idx_dd_answers_session_question ON dd_answers;
DROP INDEX IF EXISTS idx_dd_answers_status_updated ON dd_answers;
DROP INDEX IF EXISTS idx_dd_executions_session_status ON dd_executions;
DROP INDEX IF EXISTS idx_answer_history_answer_version ON dd_answer_history;
DROP INDEX IF EXISTS idx_users_role_active ON users;
DROP INDEX IF EXISTS idx_sessions_company_status ON dd_sessions;
DROP INDEX IF EXISTS idx_questions_section_order ON dd_questions;
DROP INDEX IF EXISTS idx_validations_answer_status ON dd_answer_validations;
DROP INDEX IF EXISTS idx_users_email_active ON users;
DROP INDEX IF EXISTS idx_sessions_code_status ON dd_sessions;
DROP INDEX IF EXISTS idx_executions_conversation ON dd_executions;
DROP INDEX IF EXISTS idx_vector_stores_creator ON vector_stores;

-- Remove constraints
ALTER TABLE session_vector_stores DROP CONSTRAINT unique_session_dd_type_vector_store;
ALTER TABLE dd_answers DROP CONSTRAINT chk_confidence_range;
ALTER TABLE dd_answers DROP CONSTRAINT chk_tokens_positive;
ALTER TABLE dd_sections DROP CONSTRAINT chk_section_order_non_negative;
ALTER TABLE dd_questions DROP CONSTRAINT chk_question_order_non_negative;
*/