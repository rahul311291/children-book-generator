/*
  # Fix Templates ID Column to Use UUID with Auto-Generation

  ## Changes Made
  
  1. **Update templates.id column**
     - Change from TEXT to UUID
     - Add DEFAULT gen_random_uuid() for automatic ID generation
     - Preserve existing template data by generating UUID for current row
  
  2. **Update foreign key references**
     - Update template_pages.template_id to match new UUID
     - Recreate foreign key constraint with UUID type
  
  3. **Preserve data integrity**
     - Existing "when_i_grow_up" template is migrated with a generated UUID
     - All 24 template pages are updated to reference the new UUID
  
  ## Security
  - RLS policies already exist and remain unchanged
  - Public INSERT and SELECT access maintained
  
  ## Important Notes
  - This is a one-time migration to convert from human-readable IDs to auto-generated UUIDs
  - After this migration, new template inserts won't need to provide an ID manually
  - The Python code will work without generating UUIDs explicitly
*/

-- Step 1: Generate a UUID for the existing template and store it
DO $$
DECLARE
  new_template_uuid UUID;
BEGIN
  -- Generate a new UUID for the existing template
  new_template_uuid := gen_random_uuid();
  
  -- Create a temporary column to store the new UUID
  ALTER TABLE templates ADD COLUMN IF NOT EXISTS id_new UUID;
  
  -- Set the new UUID for the existing template
  UPDATE templates SET id_new = new_template_uuid WHERE id = 'when_i_grow_up';
  
  -- Update template_pages to reference the new UUID
  -- First, add a temporary column
  ALTER TABLE template_pages ADD COLUMN IF NOT EXISTS template_id_new UUID;
  
  -- Update the references
  UPDATE template_pages 
  SET template_id_new = new_template_uuid 
  WHERE template_id = 'when_i_grow_up';
END $$;

-- Step 2: Drop the old foreign key constraint
ALTER TABLE template_pages DROP CONSTRAINT IF EXISTS template_pages_template_id_fkey;

-- Step 3: Drop old columns and rename new ones for templates
ALTER TABLE templates DROP COLUMN IF EXISTS id;
ALTER TABLE templates RENAME COLUMN id_new TO id;

-- Step 4: Make the new id column the primary key with default
ALTER TABLE templates ALTER COLUMN id SET NOT NULL;
ALTER TABLE templates ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE templates ADD PRIMARY KEY (id);

-- Step 5: Drop old template_id and rename new one for template_pages
ALTER TABLE template_pages DROP COLUMN IF EXISTS template_id;
ALTER TABLE template_pages RENAME COLUMN template_id_new TO template_id;
ALTER TABLE template_pages ALTER COLUMN template_id SET NOT NULL;

-- Step 6: Recreate the foreign key constraint
ALTER TABLE template_pages
  ADD CONSTRAINT template_pages_template_id_fkey
  FOREIGN KEY (template_id)
  REFERENCES templates(id)
  ON DELETE CASCADE;

-- Step 7: Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_template_pages_template_id ON template_pages(template_id);
