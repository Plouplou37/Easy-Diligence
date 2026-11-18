-- Migration: clear the placeholder section descriptions
-- Date: 2026-09-10
-- Description: dd_sections.description is now sent to the model, appended under
--   the section heading by DDProcessor.compose_question_text. Until today the
--   field was write-only -- never displayed, never sent -- and both import paths
--   defaulted it to "Section for <title>" because the Excel and CSV parsers
--   always return description = None. That filled 213 of 217 rows with a
--   restatement of the title.
--
--   Left in place, every question of every run would now carry a line saying
--   "Section for Fund basic information" right after "[Section: Fund basic
--   information]". So the placeholders go before the injection is used.
--
--   The comparison is an exact equality against the generated string, not a LIKE:
--   a description someone actually wrote must survive, even if it happens to
--   start the same way.
--
--   Both writers have been changed to leave the column NULL, so the placeholder
--   will not come back on the next import.
--
-- ⚠️ Run this BEFORE the next DD run, not after.

UPDATE dd_sections
SET description = NULL
WHERE description = CONCAT('Section for ', title);

-- Check: expected to return 0 rows afterwards.
-- SELECT id, title, description FROM dd_sections
-- WHERE description = CONCAT('Section for ', title);
