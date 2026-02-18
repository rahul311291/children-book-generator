# Instructions for Bolt: Fix Supabase Tables Schema

## Problem
The `templates` and `template_pages` tables have `id` columns that are NOT NULL but don't have default values, causing inserts to fail with:
```
'null value in column "id" violates not-null constraint'
```

## What Bolt Needs to Do

### Step 1: Check Current Schema

Run this SQL in Supabase SQL Editor to see the current table structure:

```sql
-- Check templates table schema
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'templates'
ORDER BY ordinal_position;

-- Check template_pages table schema  
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'template_pages'
ORDER BY ordinal_position;
```

### Step 2: Fix the Schema

The `id` columns should be UUID type with auto-generation. Run these SQL commands:

```sql
-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Fix templates table: Make id column UUID with default generation
ALTER TABLE templates 
ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- Ensure id is UUID type (if it's not already)
ALTER TABLE templates 
ALTER COLUMN id TYPE uuid USING id::uuid;

-- Fix template_pages table: Make id column UUID with default generation
ALTER TABLE template_pages 
ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- Ensure id is UUID type (if it's not already)
ALTER TABLE template_pages 
ALTER COLUMN id TYPE uuid USING id::uuid;
```

### Step 3: Verify the Fix

Run this to confirm the defaults are set:

```sql
-- Verify templates table
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'templates' AND column_name = 'id';

-- Verify template_pages table
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'template_pages' AND column_name = 'id';
```

Expected result:
- `data_type` should be `uuid`
- `is_nullable` should be `NO`
- `column_default` should be `gen_random_uuid()` or similar UUID generation function

### Step 4: Ensure RLS Policies Exist

Make sure these RLS policies exist (from SUPABASE_RLS_FIX.md):

```sql
-- For templates table
CREATE POLICY IF NOT EXISTS "Allow public read access to templates"
ON templates FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Allow public insert access to templates"
ON templates FOR INSERT WITH CHECK (true);

-- For template_pages table
CREATE POLICY IF NOT EXISTS "Allow public read access to template_pages"
ON template_pages FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Allow public insert access to template_pages"
ON template_pages FOR INSERT WITH CHECK (true);
```

## Alternative: If Tables Don't Exist Yet

If the tables don't exist, create them with the correct schema:

```sql
-- Create templates table
CREATE TABLE IF NOT EXISTS templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    description text,
    total_pages integer,
    created_at timestamp with time zone DEFAULT now()
);

-- Create template_pages table
CREATE TABLE IF NOT EXISTS template_pages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id uuid NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    page_number integer NOT NULL,
    profession_title text,
    text_template text,
    image_prompt_template text,
    created_at timestamp with time zone DEFAULT now(),
    UNIQUE(template_id, page_number)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_template_pages_template_id ON template_pages(template_id);
CREATE INDEX IF NOT EXISTS idx_template_pages_page_number ON template_pages(template_id, page_number);
```

## Summary for Bolt

**Task:** Fix Supabase `templates` and `template_pages` tables so that:
1. `id` columns are UUID type
2. `id` columns have `DEFAULT gen_random_uuid()` so Supabase auto-generates UUIDs
3. RLS policies allow public SELECT and INSERT operations

**Why:** The Python code is trying to insert templates but the `id` column requires a value. Instead of generating UUIDs in Python, we should let Supabase handle it automatically via the DEFAULT constraint.
