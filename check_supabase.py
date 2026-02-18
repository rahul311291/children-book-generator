#!/usr/bin/env python3
"""
Diagnostic script to check Supabase connection and template data.
Run this to see what's actually in your Supabase database.

Usage:
    python check_supabase.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

def init_supabase():
    """Initialize Supabase client."""
    supabase_url = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url:
        print("❌ ERROR: Supabase URL not found!")
        print("   Set VITE_SUPABASE_URL or SUPABASE_URL environment variable")
        return None
    
    if not supabase_key:
        print("❌ ERROR: Supabase API key not found!")
        print("   Set VITE_SUPABASE_ANON_KEY or SUPABASE_ANON_KEY environment variable")
        return None

    print(f"✅ Supabase URL: {supabase_url[:50]}...")
    print(f"✅ API Key: {supabase_key[:20]}...")
    
    try:
        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully\n")
        return client
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {e}")
        return None

def main():
    print("="*60)
    print("🔍 Supabase Diagnostic Check")
    print("="*60 + "\n")
    
    supabase = init_supabase()
    if not supabase:
        sys.exit(1)
    
    # Check templates table
    print("📊 Checking 'templates' table...")
    try:
        response = supabase.table("templates").select("*").execute()
        templates = response.data or []
        
        print(f"   Found {len(templates)} template(s):\n")
        
        if templates:
            for t in templates:
                print(f"   • ID: {t.get('id')}")
                print(f"     Name: {t.get('name', 'N/A')}")
                print(f"     Description: {t.get('description', 'N/A')[:60]}...")
                print(f"     Total Pages: {t.get('total_pages', 'N/A')}")
                
                # Check pages for this template
                pages_resp = supabase.table("template_pages").select("id, page_number, profession_title").eq("template_id", t["id"]).order("page_number").execute()
                pages = pages_resp.data or []
                print(f"     Pages in DB: {len(pages)}")
                if pages:
                    print(f"     First 3 pages: {', '.join([p.get('profession_title', 'N/A') for p in pages[:3]])}")
                print()
        else:
            print("   ⚠️  No templates found in database!\n")
            
    except Exception as e:
        print(f"   ❌ ERROR reading templates table: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Check template_pages table
    print("📄 Checking 'template_pages' table...")
    try:
        pages_resp = supabase.table("template_pages").select("template_id, page_number").execute()
        pages = pages_resp.data or []
        
        # Group by template_id
        from collections import defaultdict
        pages_by_template = defaultdict(int)
        for page in pages:
            pages_by_template[page.get("template_id")] += 1
        
        print(f"   Total pages: {len(pages)}")
        print(f"   Pages grouped by template_id:")
        for template_id, count in pages_by_template.items():
            print(f"     - Template ID {template_id}: {count} pages")
        print()
        
    except Exception as e:
        print(f"   ❌ ERROR reading template_pages table: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Expected templates
    print("📚 Expected templates (from code):")
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from template_book_generator import DEFAULT_TEMPLATES
        for idx, tmpl in enumerate(DEFAULT_TEMPLATES, 1):
            print(f"   {idx}. {tmpl['name']} ({tmpl.get('total_pages', 0)} pages)")
    except Exception as e:
        print(f"   ⚠️  Could not load DEFAULT_TEMPLATES: {e}")
    
    print("\n" + "="*60)
    print("💡 Next steps:")
    print("   1. If you see fewer than 5 templates, run: python seed_templates.py")
    print("   2. Check Supabase Dashboard → Table Editor → templates")
    print("   3. Verify RLS policies allow inserts/reads")
    print("="*60)

if __name__ == "__main__":
    main()
