# Fix Supabase RLS (Row Level Security) for Templates

## Problem
The error `new row violates row-level security policy for table "templates"` means RLS is blocking inserts.

## Solution: Create RLS Policies

Go to your Supabase Dashboard and run these SQL commands:

### Step 1: Open SQL Editor
1. Go to https://supabase.com/dashboard
2. Select your project: **"children book generator"**
3. Click **SQL Editor** in the left sidebar
4. Click **New Query**

### Step 2: Run These SQL Commands

```sql
-- Allow anyone to SELECT (read) templates
CREATE POLICY "Allow public read access to templates"
ON templates
FOR SELECT
USING (true);

-- Allow anyone to INSERT templates (for seeding)
CREATE POLICY "Allow public insert access to templates"
ON templates
FOR INSERT
WITH CHECK (true);

-- Allow anyone to SELECT (read) template_pages
CREATE POLICY "Allow public read access to template_pages"
ON template_pages
FOR SELECT
USING (true);

-- Allow anyone to INSERT template_pages (for seeding)
CREATE POLICY "Allow public insert access to template_pages"
ON template_pages
FOR INSERT
WITH CHECK (true);
```

### Step 3: Verify Policies
1. Go to **Table Editor** → `templates` table
2. Click the **RLS** tab
3. You should see 2 policies:
   - "Allow public read access to templates"
   - "Allow public insert access to templates"
4. Do the same for `template_pages` table

### Step 4: Test
After creating the policies:
1. Restart your app or click "🔄 Force Reseed Templates" button
2. Check Supabase Dashboard → `templates` table - you should see 5 templates
3. Check `template_pages` table - you should see ~64 pages total

## Alternative: Disable RLS (Not Recommended for Production)

If you want to disable RLS entirely (only for testing):

```sql
-- Disable RLS on templates table
ALTER TABLE templates DISABLE ROW LEVEL SECURITY;

-- Disable RLS on template_pages table
ALTER TABLE template_pages DISABLE ROW LEVEL SECURITY;
```

**Note:** Disabling RLS is less secure. Use policies instead for production.

## Verify It Works

After applying the policies, check your app logs. You should see:
- ✅ Success messages for each template created
- No more "violates row-level security policy" errors
