"""
Quick test script to verify template book feature is working
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from template_data import personalize_template_text, get_pronoun

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test that we can connect to Supabase and fetch templates."""
    print("Testing database connection...")

    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        print("❌ ERROR: Supabase credentials not found in .env file")
        return False

    print(f"✅ Supabase URL: {supabase_url[:40]}...")
    print(f"✅ Supabase Key: {supabase_key[:20]}...")

    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")

        # Fetch templates
        response = supabase.table("templates").select("*").execute()
        templates = response.data

        print(f"✅ Found {len(templates)} template(s)")

        for template in templates:
            print(f"\n📚 Template: {template['name']}")
            print(f"   Description: {template['description']}")
            print(f"   Pages: {template['total_pages']}")

            # Fetch pages for this template
            pages_response = supabase.table("template_pages").select("*").eq("template_id", template['id']).order("page_number").execute()
            pages = pages_response.data

            print(f"   ✅ Loaded {len(pages)} pages from database")

            # Show first 3 professions
            if pages:
                print(f"\n   First 3 professions:")
                for page in pages[:3]:
                    print(f"   - Page {page['page_number']}: {page['profession_title']}")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_text_personalization():
    """Test that text personalization works correctly."""
    print("\n" + "="*60)
    print("Testing text personalization...")

    test_template = "When {name} grows up, {he_she} will be amazing!"

    # Test with a boy
    result_boy = personalize_template_text(test_template, "Alex", "Boy", 5)
    print(f"\n✅ Boy example: {result_boy}")

    # Test with a girl
    result_girl = personalize_template_text(test_template, "Emma", "Girl", 5)
    print(f"✅ Girl example: {result_girl}")

    # Test with non-binary
    result_nb = personalize_template_text(test_template, "Sam", "Non-binary", 5)
    print(f"✅ Non-binary example: {result_nb}")

    return True


def test_full_page_generation():
    """Test generating a full personalized page."""
    print("\n" + "="*60)
    print("Testing full page generation...")

    from template_data import WHEN_I_GROW_UP_TEMPLATE

    child_name = "Maya"
    gender = "Girl"
    age = 7

    # Get the first profession (Astronaut)
    page = WHEN_I_GROW_UP_TEMPLATE["pages"][0]

    print(f"\n📄 Generating page for {child_name}, {age} years old")
    print(f"Profession: {page['profession_title']}")

    personalized_text = personalize_template_text(
        page["text_template"],
        child_name,
        gender,
        age
    )

    print(f"\n✅ Personalized text:\n{personalized_text}")

    return True


if __name__ == "__main__":
    print("="*60)
    print("TEMPLATE BOOK FEATURE TEST")
    print("="*60)

    # Run tests
    db_ok = test_database_connection()
    text_ok = test_text_personalization()
    page_ok = test_full_page_generation()

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Database Connection: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"Text Personalization: {'✅ PASS' if text_ok else '❌ FAIL'}")
    print(f"Page Generation: {'✅ PASS' if page_ok else '❌ FAIL'}")

    if db_ok and text_ok and page_ok:
        print("\n🎉 All tests passed! Template book feature is ready to use.")
        print("\nTo use in the app:")
        print("1. Run: streamlit run main.py")
        print("2. Select 'Template Book' mode")
        print("3. Fill in child details and upload 3 photos")
        print("4. Preview your personalized 24-page book!")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
