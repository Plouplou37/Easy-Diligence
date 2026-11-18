-- Migration: index dd_answers for the dashboard counters
-- Date: 2026-09-16
-- Description: GET /api/dashboard/sessions counts the current answers of every
--   visible session by status, in one grouped query filtered on session_id and
--   is_current. dd_answers has indexes on execution_id, status and is_current,
--   none starting with session_id.
--
--   MySQL syntax (017_performance_indexes.sql is Postgres). Optional: the
--   endpoint works without it, only slower as dd_answers grows.
--   Apply by hand, like 021-025. If it was already applied, MySQL answers
--   "Duplicate key name" and changes nothing.

CREATE INDEX idx_dd_answers_session_current_status
    ON dd_answers (session_id, is_current, status);
