/*
  # Add Cover Image to Templates
  
  ## Changes
    - Add `cover_image` column to `templates` table to store cover image URLs
  
  ## Details
    - Column is nullable to support existing templates
    - Will be populated with cover images for each template
*/

-- Add cover_image column to templates table
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'templates' AND column_name = 'cover_image'
  ) THEN
    ALTER TABLE templates ADD COLUMN cover_image text;
  END IF;
END $$;
