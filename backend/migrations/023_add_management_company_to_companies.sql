-- Migration: Split the fund from its management company
-- Date: 2026-09-09
-- Description: A DD subject is a fund (companies.name) run by a management
--              company. Until now only one name existed, so the model -- and
--              therefore the web search -- had to guess which entity a question
--              was about. These columns let the system prompt name both.
--              NULL stays valid: existing companies keep working, the prompt
--              simply omits the manager when it is unknown.

ALTER TABLE companies
  ADD COLUMN management_company_name VARCHAR(255) NULL
    COMMENT 'Legal name of the management company running the fund',
  ADD COLUMN management_company_website VARCHAR(500) NULL
    COMMENT 'Website of the management company (used to steer web search)';
