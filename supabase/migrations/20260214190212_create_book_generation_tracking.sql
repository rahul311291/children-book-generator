/*
  # Book Generation Tracking System

  1. New Tables
    - `book_generation_jobs`
      - `id` (uuid, primary key) - Unique job identifier
      - `template_id` (text) - Template being used
      - `template_name` (text) - Name of the template
      - `child_name` (text) - Child's name for personalization
      - `child_age` (integer) - Child's age
      - `child_gender` (text) - Child's gender
      - `status` (text) - Job status: 'in_progress', 'completed', 'failed', 'paused'
      - `total_pages` (integer) - Total pages to generate
      - `pages_completed` (integer) - Number of pages successfully generated
      - `current_page` (integer) - Current page being processed
      - `error_message` (text, nullable) - Error details if failed
      - `error_page` (integer, nullable) - Page number where error occurred
      - `created_at` (timestamptz) - When job was created
      - `updated_at` (timestamptz) - Last update time
      - `completed_at` (timestamptz, nullable) - When job completed
      
    - `book_generation_pages`
      - `id` (uuid, primary key) - Unique page identifier
      - `job_id` (uuid, foreign key) - Reference to job
      - `page_number` (integer) - Page number in book
      - `profession_title` (text) - Profession for this page
      - `text` (text) - Personalized text content
      - `image_prompt` (text) - Prompt used to generate image
      - `image_url` (text, nullable) - Base64 or URL of generated image
      - `status` (text) - Page status: 'pending', 'generating', 'completed', 'failed'
      - `error_message` (text, nullable) - Error if page generation failed
      - `generation_attempts` (integer) - Number of generation attempts
      - `created_at` (timestamptz) - When page record was created
      - `completed_at` (timestamptz, nullable) - When page generation completed

  2. Security
    - Enable RLS on both tables
    - Public access for read (since this is a demo app)
    - Public access for write (since there's no auth yet)
    
  3. Indexes
    - Index on job_id in pages table for fast lookups
    - Index on status for filtering jobs
    - Index on created_at for sorting by date
*/

-- Create book_generation_jobs table
CREATE TABLE IF NOT EXISTS book_generation_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id text NOT NULL,
  template_name text NOT NULL,
  child_name text NOT NULL,
  child_age integer NOT NULL,
  child_gender text NOT NULL,
  status text NOT NULL DEFAULT 'in_progress',
  total_pages integer NOT NULL DEFAULT 0,
  pages_completed integer NOT NULL DEFAULT 0,
  current_page integer NOT NULL DEFAULT 0,
  error_message text,
  error_page integer,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Create book_generation_pages table
CREATE TABLE IF NOT EXISTS book_generation_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES book_generation_jobs(id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  profession_title text NOT NULL DEFAULT '',
  text text NOT NULL DEFAULT '',
  image_prompt text NOT NULL DEFAULT '',
  image_url text,
  status text NOT NULL DEFAULT 'pending',
  error_message text,
  generation_attempts integer NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_book_generation_pages_job_id ON book_generation_pages(job_id);
CREATE INDEX IF NOT EXISTS idx_book_generation_jobs_status ON book_generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_book_generation_jobs_created_at ON book_generation_jobs(created_at DESC);

-- Enable Row Level Security
ALTER TABLE book_generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_generation_pages ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (demo app without auth)
CREATE POLICY "Allow public read access to jobs"
  ON book_generation_jobs
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Allow public insert to jobs"
  ON book_generation_jobs
  FOR INSERT
  TO public
  WITH CHECK (true);

CREATE POLICY "Allow public update to jobs"
  ON book_generation_jobs
  FOR UPDATE
  TO public
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow public delete to jobs"
  ON book_generation_jobs
  FOR DELETE
  TO public
  USING (true);

CREATE POLICY "Allow public read access to pages"
  ON book_generation_pages
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Allow public insert to pages"
  ON book_generation_pages
  FOR INSERT
  TO public
  WITH CHECK (true);

CREATE POLICY "Allow public update to pages"
  ON book_generation_pages
  FOR UPDATE
  TO public
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow public delete to pages"
  ON book_generation_pages
  FOR DELETE
  TO public
  USING (true);

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS update_book_generation_jobs_updated_at ON book_generation_jobs;
CREATE TRIGGER update_book_generation_jobs_updated_at
  BEFORE UPDATE ON book_generation_jobs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();