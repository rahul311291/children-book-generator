# Render.com Environment Variables Setup

To fix the "[Errno -2] Name or service not known" error, you need to add these environment variables to your Render.com service.

## How to Add Environment Variables on Render.com

1. Go to your Render.com dashboard
2. Click on your service (the Children's Book Generator)
3. Click on "Environment" in the left sidebar
4. Click "Add Environment Variable" for each variable below
5. After adding all variables, click "Save Changes"
6. Render will automatically redeploy your service

## Required Environment Variables

Add these **exact** key-value pairs:

### Supabase Connection (Required for Template Books & Job Tracking)

**Variable Name:** `VITE_SUPABASE_URL`
**Value:** `https://zmkqigxpnxrwmbwfmkiv.supabase.co`

**Variable Name:** `VITE_SUPABASE_ANON_KEY`
**Value:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpta3FpZ3hwbnhyd21id2Zta2l2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwODM4NjgsImV4cCI6MjA4NjY1OTg2OH0.tnoNk6jaF2qxmggGynoJraZaZsu5GIUFY-iwgsqkmbQ`

### Optional: Google Gemini API Key (if you want a default key)

**Variable Name:** `GEMINI_API_KEY`
**Value:** `your-api-key-here` (if you want to pre-configure one)

## Quick Copy-Paste Format

Copy each line and paste into Render:

```
VITE_SUPABASE_URL=https://zmkqigxpnxrwmbwfmkiv.supabase.co
```

```
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpta3FpZ3hwbnhyd21id2Zta2l2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwODM4NjgsImV4cCI6MjA4NjY1OTg2OH0.tnoNk6jaF2qxmggGynoJraZaZsu5GIUFY-iwgsqkmbQ
```

## Verification

After adding the environment variables and redeploying:

1. Wait for the deployment to complete
2. Open your app
3. Try to create a template book
4. The error should be gone
5. You should see templates available
6. Job tracking will work automatically

## Troubleshooting

**Still getting the error after adding variables?**
- Make sure you clicked "Save Changes" in Render
- Wait for the automatic redeploy to complete (check the "Events" tab)
- Verify the variable names are exactly as shown (case-sensitive)
- Make sure there are no extra spaces in the values

**Can't see the Environment tab?**
- Make sure you're logged into the correct Render account
- Make sure you're viewing your deployed service (not the blueprint)

**Need to check if variables are set?**
- In Render, go to your service → Environment
- You should see both variables listed

## What These Variables Do

- **VITE_SUPABASE_URL**: Connects your app to the Supabase database for storing templates, job history, and generated images
- **VITE_SUPABASE_ANON_KEY**: Authenticates your app with Supabase (this is a public anonymous key, safe to expose)
- **GEMINI_API_KEY** (optional): Default API key for Google Gemini, users can still enter their own

## Security Note

The `VITE_SUPABASE_ANON_KEY` is designed to be public and is protected by Row Level Security (RLS) policies in the database. It's safe to use in client-side applications.
