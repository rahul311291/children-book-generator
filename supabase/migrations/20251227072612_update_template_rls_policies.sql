/*
  # Update RLS Policies for Template Management

  ## Overview
  Updates RLS policies for templates and template_pages tables to allow
  insert and update operations for populating template data.

  ## Changes
  - Add INSERT policy for templates table
  - Add UPDATE policy for templates table
  - Add INSERT policy for template_pages table
  - Add UPDATE policy for template_pages table
  - Add DELETE policy for template_pages table (for updates)

  ## Security Notes
  - For MVP, these are open policies to allow template management
  - In production, these should be restricted to admin users only
*/

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow insert templates" ON templates;
DROP POLICY IF EXISTS "Allow update templates" ON templates;
DROP POLICY IF EXISTS "Allow insert template pages" ON template_pages;
DROP POLICY IF EXISTS "Allow update template pages" ON template_pages;
DROP POLICY IF EXISTS "Allow delete template pages" ON template_pages;

-- RLS Policies for templates (allow all operations for MVP)
CREATE POLICY "Allow insert templates"
  ON templates FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Allow update templates"
  ON templates FOR UPDATE
  USING (true)
  WITH CHECK (true);

-- RLS Policies for template_pages (allow all operations for MVP)
CREATE POLICY "Allow insert template pages"
  ON template_pages FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Allow update template pages"
  ON template_pages FOR UPDATE
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow delete template pages"
  ON template_pages FOR DELETE
  USING (true);
