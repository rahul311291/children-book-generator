#!/usr/bin/env python3
"""
Manual script to seed all 5 templates into Supabase.
Run this if templates aren't being seeded automatically.

Usage:
    python seed_templates.py
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

# Import templates
sys.path.insert(0, str(Path(__file__).parent))
from template_book_generator import DEFAULT_TEMPLATES, seed_default_templates_if_missing

def init_supabase():
    """Initialize Supabase client."""
    supabase_url = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        print("❌ ERROR: Supabase credentials not found!")
        print("Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY environment variables")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)

def main():
    print("🌱 Seeding templates into Supabase...")
    print(f"📚 Found {len(DEFAULT_TEMPLATES)} templates to seed:\n")
    
    for idx, tmpl in enumerate(DEFAULT_TEMPLATES, 1):
        print(f"{idx}. {tmpl['name']} ({tmpl.get('total_pages', 0)} pages)")
    
    print("\n" + "="*50)
    
    try:
        supabase = init_supabase()
        seed_default_templates_if_missing(supabase)
        
        # Verify
        response = supabase.table("templates").select("*").execute()
        templates = response.data or []
        
        print("\n✅ Seeding complete!")
        print(f"📊 Found {len(templates)} templates in Supabase:")
        for t in templates:
            pages_resp = supabase.table("template_pages").select("id").eq("template_id", t["id"]).execute()
            page_count = len(pages_resp.data) if pages_resp.data else 0
            print(f"  - {t['name']} (ID: {t['id']}, Pages: {page_count})")
        
        if len(templates) < 5:
            print(f"\n⚠️  WARNING: Expected 5 templates but found {len(templates)}")
            print("Check the logs above for any errors.")
        else:
            print("\n🎉 All 5 templates are present!")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
