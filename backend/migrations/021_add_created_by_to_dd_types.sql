-- Migration: Add created_by column to dd_types table
-- Date: 2026-06-23
-- Description: Per-user ownership of DD types. NULL = shared system template
--              (visible to everyone). Existing non-system types are assigned to
--              the first admin user. System types stay shared (created_by NULL).

-- Add created_by column with FK to users
ALTER TABLE dd_types
  ADD COLUMN created_by INT NULL
    COMMENT 'Owner user id; NULL = shared system template',
  ADD CONSTRAINT fk_dd_types_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- Assign existing non-system DD types to the first admin user.
-- System types (is_system = 1) keep created_by = NULL so they remain shared.
UPDATE dd_types
   SET created_by = (SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1)
 WHERE is_system = 0;
