-- Migration: Create dd_summary_batches table
-- Date: 2026-09-10
-- Description: Tracks the OpenAI Batch job that produces the section summaries
--   of one (session, DD type). Batch bills at half the synchronous rate but its
--   only completion window is 24h, so the job outlives any request and the state
--   has to be persisted: BackgroundTasks are in-process and do not survive a
--   restart. The frontend polls this row.
--
--   Only the section summaries are batched. The final synthesis is built from
--   them, so it stays a synchronous call made when the batch is collected --
--   batching it too would chain a second 24h window.
--
--   status holds OpenAI's own values (validating, in_progress, completed,
--   failed, expired, cancelled) plus 'collected' once the results are stored.
--
--   One row per (session, dd_type): relaunching replaces the previous job.
--
-- Note: also auto-created by Base.metadata.create_all at startup; this file is
-- the record of the change for an existing database.

CREATE TABLE IF NOT EXISTS dd_summary_batches (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    dd_type_id INT NOT NULL,
    openai_batch_id VARCHAR(255) NOT NULL,
    input_file_id VARCHAR(255) NULL,
    output_file_id VARCHAR(255) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'validating',
    error_message TEXT NULL,
    created_by INT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_dd_summary_batches_session FOREIGN KEY (session_id) REFERENCES dd_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_dd_summary_batches_dd_type FOREIGN KEY (dd_type_id) REFERENCES dd_types(id),
    CONSTRAINT fk_dd_summary_batches_created_by FOREIGN KEY (created_by) REFERENCES users(id),
    CONSTRAINT unique_session_ddtype_summary_batch UNIQUE (session_id, dd_type_id),
    INDEX idx_dd_summary_batches_openai_batch_id (openai_batch_id)
);
