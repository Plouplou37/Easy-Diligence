-- Migration: Create dd_summaries table
-- Date: 2026-06-23
-- Description: Stores generated DD summaries attached to a session.
--   section_id NULL  -> DD-type-level synthesis (readable report body)
--   section_id set    -> per-section summary (shown in the PDF annex)
--   One current summary per (session, dd_type, section) scope.

CREATE TABLE IF NOT EXISTS dd_summaries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    dd_type_id INT NOT NULL,
    section_id INT NULL,
    summary_text TEXT NOT NULL,
    edited_by INT NULL,
    generated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_dd_summaries_session FOREIGN KEY (session_id) REFERENCES dd_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_dd_summaries_dd_type FOREIGN KEY (dd_type_id) REFERENCES dd_types(id),
    CONSTRAINT fk_dd_summaries_section FOREIGN KEY (section_id) REFERENCES dd_sections(id) ON DELETE CASCADE,
    CONSTRAINT fk_dd_summaries_edited_by FOREIGN KEY (edited_by) REFERENCES users(id),
    CONSTRAINT unique_session_ddtype_section_summary UNIQUE (session_id, dd_type_id, section_id)
);
