BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    username VARCHAR(100) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    full_name VARCHAR(255), 
    company VARCHAR(255), 
    phone VARCHAR(50), 
    role VARCHAR(50), 
    is_active BOOLEAN, 
    is_verified BOOLEAN, 
    last_login TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_users PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE companies (
    id SERIAL NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    website_url VARCHAR(500), 
    description TEXT, 
    management_company_name VARCHAR(255), 
    management_company_website VARCHAR(500), 
    created_by INTEGER, 
    updated_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_companies PRIMARY KEY (id), 
    CONSTRAINT fk_companies_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
    CONSTRAINT fk_companies_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id)
);

CREATE INDEX ix_companies_created_by ON companies (created_by);

CREATE INDEX ix_companies_name ON companies (name);

CREATE INDEX ix_companies_updated_by ON companies (updated_by);

CREATE TABLE dd_types (
    id SERIAL NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    icon VARCHAR(10), 
    is_active BOOLEAN, 
    is_system BOOLEAN, 
    is_validated BOOLEAN, 
    order_index INTEGER, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_types PRIMARY KEY (id), 
    CONSTRAINT fk_dd_types_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_dd_types_code ON dd_types (code);

CREATE INDEX ix_dd_types_created_by ON dd_types (created_by);

CREATE TABLE user_sessions (
    id SERIAL NOT NULL, 
    user_id INTEGER, 
    access_token_hash VARCHAR(64) NOT NULL, 
    refresh_token_hash VARCHAR(64), 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ip_address VARCHAR(45), 
    user_agent TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_user_sessions PRIMARY KEY (id), 
    CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_sessions_access_token_hash UNIQUE (access_token_hash), 
    CONSTRAINT uq_user_sessions_refresh_token_hash UNIQUE (refresh_token_hash)
);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE TABLE vector_stores (
    id VARCHAR(255) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    created_by INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_vector_stores PRIMARY KEY (id), 
    CONSTRAINT fk_vector_stores_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_vector_stores_created_by ON vector_stores (created_by);

CREATE TABLE dd_sections (
    id SERIAL NOT NULL, 
    dd_type_id INTEGER NOT NULL, 
    section_code VARCHAR(50) NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    description TEXT, 
    order_index INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_sections PRIMARY KEY (id), 
    CONSTRAINT ck_dd_sections_order_non_negative CHECK (order_index >= 0), 
    CONSTRAINT fk_dd_sections_dd_type_id_dd_types FOREIGN KEY(dd_type_id) REFERENCES dd_types (id)
);

CREATE INDEX ix_dd_sections_dd_type_order ON dd_sections (dd_type_id, order_index);

CREATE TABLE dd_sessions (
    id SERIAL NOT NULL, 
    session_code VARCHAR(50), 
    company_id INTEGER NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    status VARCHAR(50), 
    created_by INTEGER, 
    assigned_to INTEGER, 
    dd_types_json TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_sessions PRIMARY KEY (id), 
    CONSTRAINT fk_dd_sessions_assigned_to_users FOREIGN KEY(assigned_to) REFERENCES users (id), 
    CONSTRAINT fk_dd_sessions_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id), 
    CONSTRAINT fk_dd_sessions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
    CONSTRAINT ck_dd_sessions_session_status CHECK (status IN ('CREATED', 'DOCUMENTS_UPLOADED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'PAUSED'))
);

CREATE INDEX ix_dd_sessions_assigned_to ON dd_sessions (assigned_to);

CREATE INDEX ix_dd_sessions_company_status ON dd_sessions (company_id, status);

CREATE INDEX ix_dd_sessions_created_by ON dd_sessions (created_by);

CREATE UNIQUE INDEX ix_dd_sessions_session_code ON dd_sessions (session_code);

CREATE TABLE dd_executions (
    id SERIAL NOT NULL, 
    session_id INTEGER NOT NULL, 
    dd_type_id INTEGER NOT NULL, 
    status VARCHAR(50), 
    conversation_id VARCHAR(255), 
    validator_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_executions PRIMARY KEY (id), 
    CONSTRAINT fk_dd_executions_dd_type_id_dd_types FOREIGN KEY(dd_type_id) REFERENCES dd_types (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_dd_executions_session_id_dd_sessions FOREIGN KEY(session_id) REFERENCES dd_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT fk_dd_executions_validator_id_users FOREIGN KEY(validator_id) REFERENCES users (id), 
    CONSTRAINT uq_dd_executions_conversation_id UNIQUE (conversation_id)
);

CREATE INDEX ix_dd_executions_dd_type_id ON dd_executions (dd_type_id);

CREATE INDEX ix_dd_executions_session_status ON dd_executions (session_id, status);

CREATE TABLE dd_questions (
    id SERIAL NOT NULL, 
    section_id INTEGER NOT NULL, 
    question_code VARCHAR(50) NOT NULL, 
    question_text TEXT NOT NULL, 
    context_prompt TEXT, 
    order_index INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_questions PRIMARY KEY (id), 
    CONSTRAINT ck_dd_questions_order_non_negative CHECK (order_index >= 0), 
    CONSTRAINT fk_dd_questions_section_id_dd_sections FOREIGN KEY(section_id) REFERENCES dd_sections (id)
);

CREATE INDEX ix_dd_questions_section_order ON dd_questions (section_id, order_index);

CREATE TABLE dd_summaries (
    id SERIAL NOT NULL, 
    session_id INTEGER NOT NULL, 
    dd_type_id INTEGER NOT NULL, 
    section_id INTEGER, 
    summary_text TEXT NOT NULL, 
    edited_by INTEGER, 
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_summaries PRIMARY KEY (id), 
    CONSTRAINT fk_dd_summaries_dd_type_id_dd_types FOREIGN KEY(dd_type_id) REFERENCES dd_types (id), 
    CONSTRAINT fk_dd_summaries_edited_by_users FOREIGN KEY(edited_by) REFERENCES users (id), 
    CONSTRAINT fk_dd_summaries_section_id_dd_sections FOREIGN KEY(section_id) REFERENCES dd_sections (id) ON DELETE CASCADE, 
    CONSTRAINT fk_dd_summaries_session_id_dd_sessions FOREIGN KEY(session_id) REFERENCES dd_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT unique_session_ddtype_section_summary UNIQUE (session_id, dd_type_id, section_id)
);

CREATE INDEX ix_dd_summaries_section_id ON dd_summaries (section_id);

CREATE TABLE dd_summary_batches (
    id SERIAL NOT NULL, 
    session_id INTEGER NOT NULL, 
    dd_type_id INTEGER NOT NULL, 
    openai_batch_id VARCHAR(255) NOT NULL, 
    input_file_id VARCHAR(255), 
    output_file_id VARCHAR(255), 
    status VARCHAR(50) NOT NULL, 
    error_message TEXT, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_summary_batches PRIMARY KEY (id), 
    CONSTRAINT fk_dd_summary_batches_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
    CONSTRAINT fk_dd_summary_batches_dd_type_id_dd_types FOREIGN KEY(dd_type_id) REFERENCES dd_types (id), 
    CONSTRAINT fk_dd_summary_batches_session_id_dd_sessions FOREIGN KEY(session_id) REFERENCES dd_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT unique_session_ddtype_summary_batch UNIQUE (session_id, dd_type_id)
);

CREATE INDEX ix_dd_summary_batches_openai_batch_id ON dd_summary_batches (openai_batch_id);

CREATE TABLE session_vector_stores (
    id SERIAL NOT NULL, 
    session_id INTEGER NOT NULL, 
    dd_type_id INTEGER, 
    vector_store_id VARCHAR(255) NOT NULL, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    assigned_by INTEGER NOT NULL, 
    CONSTRAINT pk_session_vector_stores PRIMARY KEY (id), 
    CONSTRAINT fk_session_vector_stores_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id), 
    CONSTRAINT fk_session_vector_stores_session_id_dd_sessions FOREIGN KEY(session_id) REFERENCES dd_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT fk_session_vector_stores_vector_store_id_vector_stores FOREIGN KEY(vector_store_id) REFERENCES vector_stores (id)
);

CREATE INDEX ix_session_vector_stores_session_id ON session_vector_stores (session_id);

CREATE INDEX ix_session_vector_stores_vector_store_id ON session_vector_stores (vector_store_id);

CREATE TABLE dd_responses (
    id SERIAL NOT NULL, 
    execution_id INTEGER NOT NULL, 
    response_id VARCHAR(255) NOT NULL, 
    previous_response_id VARCHAR(255), 
    openai_response JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_responses PRIMARY KEY (id), 
    CONSTRAINT fk_dd_responses_execution_id_dd_executions FOREIGN KEY(execution_id) REFERENCES dd_executions (id) ON DELETE CASCADE, 
    CONSTRAINT fk_dd_responses_previous_response_id_dd_responses FOREIGN KEY(previous_response_id) REFERENCES dd_responses (response_id), 
    CONSTRAINT uq_dd_responses_response_id UNIQUE (response_id)
);

CREATE INDEX ix_dd_responses_execution_id ON dd_responses (execution_id);

CREATE INDEX ix_dd_responses_previous_response_id ON dd_responses (previous_response_id);

CREATE TABLE dd_answers (
    id SERIAL NOT NULL, 
    session_id INTEGER NOT NULL, 
    execution_id INTEGER, 
    section_code VARCHAR(50) NOT NULL, 
    question_code VARCHAR(50) NOT NULL, 
    section_id INTEGER, 
    question_id INTEGER, 
    dd_type_id INTEGER, 
    version INTEGER, 
    is_current BOOLEAN, 
    status VARCHAR(50), 
    edited_by INTEGER, 
    edited_at TIMESTAMP WITH TIME ZONE, 
    answer_text TEXT, 
    sources JSONB, 
    confidence_score FLOAT, 
    tokens_used INTEGER, 
    response_id VARCHAR(255), 
    retry_count INTEGER, 
    error_type VARCHAR(50), 
    error_message TEXT, 
    last_error_at TIMESTAMP WITH TIME ZONE, 
    answered_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_answers PRIMARY KEY (id), 
    CONSTRAINT ck_dd_answers_confidence_range CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)), 
    CONSTRAINT ck_dd_answers_tokens_non_negative CHECK (tokens_used >= 0), 
    CONSTRAINT fk_dd_answers_dd_type_id_dd_types FOREIGN KEY(dd_type_id) REFERENCES dd_types (id), 
    CONSTRAINT fk_dd_answers_edited_by_users FOREIGN KEY(edited_by) REFERENCES users (id), 
    CONSTRAINT fk_dd_answers_execution_id_dd_executions FOREIGN KEY(execution_id) REFERENCES dd_executions (id) ON DELETE CASCADE, 
    CONSTRAINT fk_dd_answers_question_id_dd_questions FOREIGN KEY(question_id) REFERENCES dd_questions (id), 
    CONSTRAINT fk_dd_answers_response_id_dd_responses FOREIGN KEY(response_id) REFERENCES dd_responses (response_id) ON DELETE SET NULL, 
    CONSTRAINT fk_dd_answers_section_id_dd_sections FOREIGN KEY(section_id) REFERENCES dd_sections (id), 
    CONSTRAINT fk_dd_answers_session_id_dd_sessions FOREIGN KEY(session_id) REFERENCES dd_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT ck_dd_answers_answer_status CHECK (status IN ('COMPLETED', 'FAILED', 'DRAFT', 'NEEDS_REVIEW', 'APPROVED', 'REJECTED')), 
    CONSTRAINT ck_dd_answers_error_type CHECK (error_type IN ('rate_limit', 'context_overflow', 'api_error', 'network_error', 'validation_error', 'timeout', 'unknown'))
);

CREATE INDEX ix_dd_answers_dd_type_id ON dd_answers (dd_type_id);

CREATE INDEX ix_dd_answers_execution_status ON dd_answers (execution_id, status);

CREATE INDEX ix_dd_answers_question_id ON dd_answers (question_id);

CREATE INDEX ix_dd_answers_response_id ON dd_answers (response_id);

CREATE INDEX ix_dd_answers_section_id ON dd_answers (section_id);

CREATE INDEX ix_dd_answers_session_current_status ON dd_answers (session_id, is_current, status);

CREATE TABLE dd_messages (
    id SERIAL NOT NULL, 
    response_id VARCHAR(255) NOT NULL, 
    message_index INTEGER NOT NULL, 
    role VARCHAR(50) NOT NULL, 
    content TEXT, 
    tool_calls JSONB, 
    openai_message_id VARCHAR(255), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_messages PRIMARY KEY (id), 
    CONSTRAINT fk_dd_messages_response_id_dd_responses FOREIGN KEY(response_id) REFERENCES dd_responses (response_id) ON DELETE CASCADE, 
    CONSTRAINT uq_message_response_index UNIQUE (response_id, message_index)
);

CREATE INDEX ix_dd_messages_openai_message_id ON dd_messages (openai_message_id);

CREATE TABLE dd_answer_history (
    id SERIAL NOT NULL, 
    answer_id INTEGER NOT NULL, 
    version INTEGER NOT NULL, 
    content TEXT NOT NULL, 
    sources JSONB, 
    edited_by INTEGER, 
    edit_reason TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_dd_answer_history PRIMARY KEY (id), 
    CONSTRAINT fk_dd_answer_history_answer_id_dd_answers FOREIGN KEY(answer_id) REFERENCES dd_answers (id) ON DELETE CASCADE, 
    CONSTRAINT fk_dd_answer_history_edited_by_users FOREIGN KEY(edited_by) REFERENCES users (id)
);

CREATE INDEX ix_dd_answer_history_answer_version ON dd_answer_history (answer_id, version);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

ALTER TABLE dd_answers DROP CONSTRAINT ck_dd_answers_answer_status;

ALTER TABLE users ALTER COLUMN role SET NOT NULL;

ALTER TABLE users ALTER COLUMN role SET DEFAULT 'analyst';

ALTER TABLE users ALTER COLUMN is_active SET NOT NULL;

ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true;

ALTER TABLE users ALTER COLUMN is_verified SET NOT NULL;

ALTER TABLE users ALTER COLUMN is_verified SET DEFAULT false;

ALTER TABLE users ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE user_sessions ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_types ALTER COLUMN is_active SET NOT NULL;

ALTER TABLE dd_types ALTER COLUMN is_active SET DEFAULT true;

ALTER TABLE dd_types ALTER COLUMN is_system SET NOT NULL;

ALTER TABLE dd_types ALTER COLUMN is_system SET DEFAULT false;

ALTER TABLE dd_types ALTER COLUMN is_validated SET NOT NULL;

ALTER TABLE dd_types ALTER COLUMN is_validated SET DEFAULT false;

ALTER TABLE dd_types ALTER COLUMN order_index SET NOT NULL;

ALTER TABLE dd_types ALTER COLUMN order_index SET DEFAULT 0;

ALTER TABLE dd_types ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_types ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE dd_sessions ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_sessions ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE dd_executions ALTER COLUMN status SET NOT NULL;

ALTER TABLE dd_executions ALTER COLUMN status SET DEFAULT 'not_started';

ALTER TABLE dd_executions ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_executions ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN version SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN version SET DEFAULT 1;

ALTER TABLE dd_answers ALTER COLUMN is_current SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN is_current SET DEFAULT true;

ALTER TABLE dd_answers ALTER COLUMN status SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN status SET DEFAULT 'needs_review';

ALTER TABLE dd_answers ALTER COLUMN tokens_used SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN tokens_used SET DEFAULT 0;

ALTER TABLE dd_answers ALTER COLUMN retry_count SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN retry_count SET DEFAULT 0;

ALTER TABLE dd_answers ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE dd_sections ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_questions ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_summaries ALTER COLUMN generated_at SET NOT NULL;

ALTER TABLE dd_summary_batches ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE session_vector_stores ALTER COLUMN assigned_at SET NOT NULL;

ALTER TABLE dd_responses ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_messages ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_answer_history ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE vector_stores ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN execution_id SET NOT NULL;

ALTER TABLE dd_answers ALTER COLUMN question_id SET NOT NULL;

ALTER TABLE user_sessions ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE dd_answers ADD CONSTRAINT ck_dd_answers_answer_status CHECK (status IN ('completed', 'failed', 'draft', 'needs_review', 'approved', 'rejected'));

ALTER TABLE dd_executions ADD CONSTRAINT ck_dd_executions_execution_status CHECK (status IN ('not_started', 'in_progress', 'generated', 'failed', 'paused', 'under_review', 'validated', 'finalized'));

ALTER TABLE users ADD CONSTRAINT ck_users_role CHECK (role IN ('admin', 'analyst'));

ALTER TABLE dd_executions ADD CONSTRAINT uq_dd_executions_session_id UNIQUE (session_id, dd_type_id);

ALTER TABLE dd_sections ADD CONSTRAINT uq_dd_sections_dd_type_id UNIQUE (dd_type_id, section_code);

ALTER TABLE dd_questions ADD CONSTRAINT uq_dd_questions_section_id UNIQUE (section_id, question_code);

ALTER TABLE session_vector_stores ADD CONSTRAINT uq_session_vector_stores_session_id UNIQUE (session_id, dd_type_id, vector_store_id);

CREATE UNIQUE INDEX ix_dd_answers_one_current ON dd_answers (execution_id, question_id) WHERE is_current;

CREATE UNIQUE INDEX ix_dd_summaries_one_synthesis ON dd_summaries (session_id, dd_type_id) WHERE section_id IS NULL;

CREATE UNIQUE INDEX ix_session_vector_stores_one_session_wide ON session_vector_stores (session_id, vector_store_id) WHERE dd_type_id IS NULL;

CREATE INDEX ix_session_vector_stores_dd_type_id ON session_vector_stores (dd_type_id);

ALTER TABLE session_vector_stores ADD CONSTRAINT fk_session_vector_stores_dd_type_id_dd_types FOREIGN KEY(dd_type_id) REFERENCES dd_types (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

COMMIT;

