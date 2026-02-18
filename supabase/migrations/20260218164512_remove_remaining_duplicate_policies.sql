/*
  # Clean up remaining duplicate policies
  
  Remove old policy names that weren't caught in the previous migration
*/

-- Remove old duplicate policies
DROP POLICY IF EXISTS "Allow public read access to jobs" ON book_generation_jobs;
DROP POLICY IF EXISTS "Allow public read access to pages" ON book_generation_pages;
