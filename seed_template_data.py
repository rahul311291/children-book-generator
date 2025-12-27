"""
Script to seed the template data into Supabase database
Run this once to populate the templates and template_pages tables
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from template_data import WHEN_I_GROW_UP_TEMPLATE

# Load environment variables
load_dotenv()

def seed_template_data():
    """Seed the template data into the database."""

    # Initialize Supabase client
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_ANON_KEY not found in environment variables")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # Check if template already exists
        existing = supabase.table("templates").select("*").eq("name", WHEN_I_GROW_UP_TEMPLATE["name"]).execute()

        if existing.data and len(existing.data) > 0:
            print(f"Template '{WHEN_I_GROW_UP_TEMPLATE['name']}' already exists. Updating...")
            template_id = existing.data[0]['id']

            # Update template
            supabase.table("templates").update({
                "description": WHEN_I_GROW_UP_TEMPLATE["description"],
                "total_pages": WHEN_I_GROW_UP_TEMPLATE["total_pages"]
            }).eq("id", template_id).execute()

            # Delete existing pages for this template
            supabase.table("template_pages").delete().eq("template_id", template_id).execute()
            print(f"Deleted existing pages for template {template_id}")
        else:
            # Insert new template
            print(f"Creating new template: {WHEN_I_GROW_UP_TEMPLATE['name']}")
            template_response = supabase.table("templates").insert({
                "name": WHEN_I_GROW_UP_TEMPLATE["name"],
                "description": WHEN_I_GROW_UP_TEMPLATE["description"],
                "total_pages": WHEN_I_GROW_UP_TEMPLATE["total_pages"]
            }).execute()

            template_id = template_response.data[0]['id']
            print(f"Created template with ID: {template_id}")

        # Insert all pages
        pages_data = []
        for page in WHEN_I_GROW_UP_TEMPLATE["pages"]:
            pages_data.append({
                "template_id": template_id,
                "page_number": page["page_number"],
                "profession_title": page["profession_title"],
                "text_template": page["text_template"],
                "image_prompt_template": page["image_prompt_template"]
            })

        # Insert pages in batch
        supabase.table("template_pages").insert(pages_data).execute()
        print(f"Successfully inserted {len(pages_data)} pages")

        print("\n✅ Template data seeded successfully!")
        print(f"Template: {WHEN_I_GROW_UP_TEMPLATE['name']}")
        print(f"Total Pages: {len(pages_data)}")

    except Exception as e:
        print(f"❌ Error seeding template data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    seed_template_data()
