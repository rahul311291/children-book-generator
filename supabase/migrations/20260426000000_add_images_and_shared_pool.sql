/*
  # Add image storage to book_history and shared image pool

  1. Changes
    - `book_history`: add `images` column (jsonb array of compressed base64 data URLs)

  2. New Tables
    - `shared_image_pool`
      - `id` (uuid, primary key)
      - `prompt_hash` (text, unique) — MD5 of "{template_id}:{page_number}:{age_group}:{gender}"
      - `template_id` (text)
      - `page_number` (integer)
      - `age_group` (text) — "2-4", "4-6", "6-8", "8-12"
      - `gender` (text)
      - `image_url` (text) — compressed base64 JPEG data URL
      - `created_at` (timestamptz)

  3. Security
    - shared_image_pool: readable + insertable by all authenticated users (no personal data)
    - book_history.images: protected by existing RLS on book_history
*/

-- Add images column to book_history (stores compressed base64 data URLs per page)
ALTER TABLE book_history ADD COLUMN IF NOT EXISTS images jsonb DEFAULT '[]';

-- Shared image pool: generic template images without reference photos, reusable across users
CREATE TABLE IF NOT EXISTS shared_image_pool (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_hash  text NOT NULL,
  template_id  text NOT NULL,
  page_number  integer NOT NULL,
  age_group    text NOT NULL,
  gender       text NOT NULL,
  image_url    text NOT NULL,
  created_at   timestamptz DEFAULT now()
);

-- Unique constraint prevents duplicate inserts on race conditions
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_image_pool_hash
  ON shared_image_pool (prompt_hash);

ALTER TABLE shared_image_pool ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read (generic images, no personal data)
CREATE POLICY "Authenticated users can read shared image pool"
  ON shared_image_pool FOR SELECT
  TO authenticated
  USING (true);

-- Any authenticated user can contribute a new generic image
CREATE POLICY "Authenticated users can insert into shared image pool"
  ON shared_image_pool FOR INSERT
  TO authenticated
  WITH CHECK (true);
