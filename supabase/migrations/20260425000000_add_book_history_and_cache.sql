/*
  # Add book history persistence and template book cache

  1. New Tables
    - `book_history`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references auth.users)
      - `child_name` (text)
      - `title` (text)
      - `book_type` (text) - 'custom' or 'template'
      - `template_id` (text, nullable)
      - `template_name` (text, nullable)
      - `story_data` (jsonb) - story/book content WITHOUT images
      - `metadata` (jsonb)
      - `created_at` (timestamptz)

    - `generated_book_cache`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references auth.users)
      - `template_id` (text)
      - `child_name` (text)
      - `gender` (text)
      - `age` (integer)
      - `book_data` (jsonb) - full book with compressed images
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Columns Added
    - `openrouter_api_key` on `user_profiles`

  3. Security
    - RLS enabled on both tables
    - Users can only access their own rows
*/

-- Add OpenRouter API key to user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS openrouter_api_key text;

-- 1. book_history table
CREATE TABLE IF NOT EXISTS book_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  child_name text NOT NULL,
  title text NOT NULL,
  book_type text NOT NULL DEFAULT 'custom',
  template_id text,
  template_name text,
  story_data jsonb NOT NULL DEFAULT '{}',
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE book_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own book history"
  ON book_history FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own book history"
  ON book_history FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own book history"
  ON book_history FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own book history"
  ON book_history FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- 2. generated_book_cache table
CREATE TABLE IF NOT EXISTS generated_book_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  template_id text NOT NULL,
  child_name text NOT NULL,
  gender text NOT NULL,
  age integer NOT NULL,
  book_data jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE generated_book_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own cached books"
  ON generated_book_cache FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own cached books"
  ON generated_book_cache FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cached books"
  ON generated_book_cache FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own cached books"
  ON generated_book_cache FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Index for fast cache lookup
CREATE INDEX IF NOT EXISTS idx_generated_book_cache_lookup
  ON generated_book_cache (user_id, template_id, child_name, gender, age);

-- Index for fast history lookup
CREATE INDEX IF NOT EXISTS idx_book_history_user
  ON book_history (user_id, created_at DESC);
