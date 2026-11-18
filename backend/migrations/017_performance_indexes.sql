-- Performance optimization indexes
-- This migration adds indexes to frequently queried columns to improve performance

-- Sessions table indexes (most frequently accessed)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_created_by ON dd_sessions(created_by);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_assigned_to ON dd_sessions(assigned_to);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_company_id ON dd_sessions(company_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_status ON dd_sessions(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_created_at ON dd_sessions(created_at DESC);

-- Compound index for session listing (user + company filter)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_user_company ON dd_sessions(created_by, company_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sessions_assigned_company ON dd_sessions(assigned_to, company_id);

-- Executions table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_executions_session_id ON dd_executions(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_executions_dd_type_code ON dd_executions(dd_type_code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_executions_status ON dd_executions(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_executions_updated_at ON dd_executions(updated_at DESC);

-- Compound index for execution queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_executions_session_status ON dd_executions(session_id, status);

-- Answers table indexes (heavy queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_execution_id ON dd_answers(execution_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_question_id ON dd_answers(question_id);  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_status ON dd_answers(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_is_current ON dd_answers(is_current);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_created_at ON dd_answers(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_edited_by ON dd_answers(edited_by);

-- Compound indexes for common answer queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_execution_status ON dd_answers(execution_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answers_current_status ON dd_answers(is_current, status);

-- Answer validations indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answer_validations_answer_id ON dd_answer_validations(answer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answer_validations_status ON dd_answer_validations(validation_status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answer_validations_validator_id ON dd_answer_validations(validator_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_answer_validations_created_at ON dd_answer_validations(created_at DESC);

-- Questions table indexes  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_questions_section_id ON dd_questions(section_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_questions_order_index ON dd_questions(order_index);

-- Sections table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sections_dd_type_code ON dd_sections(dd_type_code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_sections_order_index ON dd_sections(order_index);

-- Messages and responses indexes (for OpenAI integration)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_responses_execution_id ON dd_responses(execution_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_responses_created_at ON dd_responses(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_messages_response_id ON dd_messages(response_id);

-- Vector stores indexes  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_stores_session_id ON vector_stores(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_stores_status ON vector_stores(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_stores_created_at ON vector_stores(created_at DESC);

-- Users table indexes (for authentication and user lookups)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username ON users(username);  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Companies table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_created_at ON companies(created_at DESC);

-- DD Types indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_types_code ON dd_types(code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_types_is_active ON dd_types(is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_types_order_index ON dd_types(order_index);

-- Performance statistics
-- Run ANALYZE to update table statistics for query planner
ANALYZE dd_sessions;
ANALYZE dd_executions;  
ANALYZE dd_answers;
ANALYZE dd_answer_validations;
ANALYZE dd_questions;
ANALYZE dd_sections;
ANALYZE users;
ANALYZE companies;
ANALYZE dd_types;