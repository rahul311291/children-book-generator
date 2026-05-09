"""
Children's book formats - based on bestselling layouts from
Amazon.in / Flipkart 2024-2025 (Eric Carle, Sendak, Dr. Seuss, Mo Willems,
Sudha Murty, Panchatantra, Dav Pilkey, etc.)

Each format defines page count, word density, text placement, and a base
image-prompt template. Format selection drives both the story (page count,
words per page, structural rhythm) and the image prompts (composition,
where to leave clear space for text, art style modifiers).
"""

BOOK_FORMATS = [
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "minimal_top_bottom",
        "name": "Illustration top, text bottom",
        "emoji": "📗",
        "badge": "India + Global #1 bestseller",
        "age_range": "2-5",
        "page_count": 14,
        "words_per_spread": "8-15",
        "total_words": "150-250",
        "trim_size": "8x8 in (square)",
        "text_placement": "bottom_white_band",
        "text_band_pct": 30,
        "font_size_pt": 22,
        "font_style": "rounded bold sans-serif",
        "desc": "Big illo on top, simple bold text below",
        "detail": "14 pages · 8-15 words per page",
        "bestsellers": ["Very Hungry Caterpillar", "Goodnight Moon", "Brown Bear Brown Bear"],
        "image_prompt_template": (
            "Bold bright children's book illustration, square composition. {SCENE}. "
            "The illustration fills the top 70% of the page. Bottom 30% should fade to a "
            "lighter background — text will be placed there. {ART_STYLE}. High contrast, "
            "vibrant primary colors, simple shapes, expressive characters."
        ),
        "layout_visual": "illo_top_text_bottom",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "full_bleed_double",
        "name": "Full-bleed double spread",
        "emoji": "🎨",
        "badge": "Global bestseller",
        "age_range": "4-8",
        "page_count": 12,
        "words_per_spread": "20-40",
        "total_words": "350-550",
        "trim_size": "11x8.5 in (landscape)",
        "text_placement": "overlay_on_clear_area",
        "font_size_pt": 18,
        "font_style": "playful serif or hand-lettered",
        "desc": "Dramatic edge-to-edge artwork, text overlays a clear area",
        "detail": "12 pages · 20-40 words per page",
        "bestsellers": ["Where the Wild Things Are", "Dragons Love Tacos", "The Gruffalo"],
        "image_prompt_template": (
            "Panoramic full-bleed children's book illustration, landscape composition. {SCENE}. "
            "{ART_STYLE}. Rich saturated colors. Leave one quadrant (sky or ground) lighter "
            "for text overlay. Dramatic, cinematic lighting that grows in scale at the climax."
        ),
        "layout_visual": "full_bleed_double",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "illo_opposite_text",
        "name": "Full illo opposite text page",
        "emoji": "📖",
        "badge": "Classic literary bestseller",
        "age_range": "3-7",
        "page_count": 12,
        "words_per_spread": "25-50",
        "total_words": "300-600",
        "trim_size": "8.5x11 in (portrait)",
        "text_placement": "full_white_facing_page",
        "font_size_pt": 18,
        "font_style": "elegant serif or clean sans",
        "desc": "Full illustration on one page, clean text on facing page",
        "detail": "12 pages · 25-50 words per page",
        "bestsellers": ["The Gruffalo", "Green Eggs and Ham", "Grandma's Bag of Stories"],
        "image_prompt_template": (
            "Full-page children's book illustration, portrait orientation. {SCENE}. "
            "Entire page is the illustration — no text area needed; the facing page is text-only. "
            "{ART_STYLE}. Story-advancing scene with expressive characters and a rich background."
        ),
        "layout_visual": "illo_opposite_text",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "rhyming_spread",
        "name": "Rhyming spread (illo + verse)",
        "emoji": "🎵",
        "badge": "India top read-aloud",
        "age_range": "3-6",
        "page_count": 12,
        "words_per_spread": "12-20",
        "total_words": "200-300",
        "trim_size": "10x8 in (landscape)",
        "text_placement": "white_right_page_large_verse",
        "font_size_pt": 22,
        "font_style": "bold playful, varying sizes",
        "rhyme_scheme": "AABB or ABCB",
        "desc": "Illustration left, rhyming verse right - the read-aloud favourite",
        "detail": "12 pages · rhyming couplets · 12-20 words",
        "bestsellers": ["The Gruffalo", "Pete the Cat", "Oh the Places You'll Go"],
        "image_prompt_template": (
            "Full-bleed children's picture book left-page illustration, landscape orientation. "
            "{SCENE matching the verse}. {ART_STYLE}. Bold outlines, expressive characters, "
            "rich background. Composition contained on left half — right page is text-only."
        ),
        "layout_visual": "rhyming_spread",
        "story_extra_rule": "All page text MUST be in rhyming verse (AABB couplets preferred). Maintain rhythm and meter throughout.",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "speech_bubble",
        "name": "Speech bubble / dialogue-led",
        "emoji": "💬",
        "badge": "Best for early readers",
        "age_range": "4-7",
        "page_count": 14,
        "words_per_spread": "10-25",
        "total_words": "200-350",
        "trim_size": "8.5x9 in (portrait)",
        "text_placement": "speech_bubbles_above_characters",
        "font_size_pt": 20,
        "font_style": "bold rounded caps in bubbles",
        "desc": "Characters in speech bubbles - perfect for first readers",
        "detail": "14 pages · dialogue-driven · 10-25 words",
        "bestsellers": ["Elephant & Piggie", "Don't Let the Pigeon Drive the Bus", "Tinkle Junior"],
        "image_prompt_template": (
            "Simple children's book character illustration on a white or single flat-color background. "
            "{SCENE/CHARACTERS} with very expressive faces and body language, large and centered in frame. "
            "{ART_STYLE}. Minimal background scenery — focus on the characters' interaction. "
            "Flat digital style, big eyes, simple shapes. Leave space above heads for speech bubbles. "
            "No text or speech bubbles in the image itself."
        ),
        "layout_visual": "speech_bubble",
        "story_extra_rule": "Story is told primarily through DIALOGUE. Each page text is back-and-forth between characters. Use action beats sparingly between dialogue.",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "spot_illustration",
        "name": "Spot illustration with flowing text",
        "emoji": "🪔",
        "badge": "Panchatantra / fable style",
        "age_range": "5-9",
        "page_count": 10,
        "words_per_spread": "40-70",
        "total_words": "600-900",
        "trim_size": "8.5x11 in (portrait)",
        "text_placement": "around_and_below_vignette",
        "font_size_pt": 16,
        "font_style": "elegant serif, classic literary",
        "desc": "Vignette illustrations with rich storytelling text - Indian fable style",
        "detail": "10 pages · ~70 words per page · classic feel",
        "bestsellers": ["Panchatantra", "Grandma's Bag of Stories", "If You Give a Mouse a Cookie"],
        "image_prompt_template": (
            "Spot illustration for a children's fable, vignette style. {SCENE}. "
            "Circular or irregular vignette composition with white/transparent background outside "
            "the main scene area. {ART_STYLE}. Warm earthy colors. Characters with expressive emotions. "
            "Classic timeless storybook style."
        ),
        "layout_visual": "spot_illustration",
        "story_extra_rule": "Use richer literary language. Stories often have a moral revealed at the end. Pacing is more thoughtful than action-driven.",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "comic_panels",
        "name": "Comic panel grid",
        "emoji": "💥",
        "badge": "ACK + Dog Man style",
        "age_range": "6-12",
        "page_count": 14,
        "words_per_spread": "40-80",
        "total_words": "700-1200",
        "trim_size": "7x10 in (portrait)",
        "text_placement": "speech_bubbles_and_caption_boxes",
        "font_size_pt": 14,
        "font_style": "bold comic rounded caps",
        "panel_layouts": ["2_panel_vertical", "3_panel_row", "4_panel_grid", "splash_page", "double_spread"],
        "desc": "Sequential panels - mythology, adventure, action",
        "detail": "14 pages · 2-4 panels per page · highest engagement",
        "bestsellers": ["Amar Chitra Katha", "Dog Man", "Diary of a Wimpy Kid"],
        "image_prompt_template": (
            "Single comic-book panel illustration for a children's book. {ACTION/DIALOGUE MOMENT}. "
            "{ART_STYLE}. Thick black outlines, dynamic character pose, expressive face. "
            "Bold flat colors / jewel tones. NO speech bubbles, NO text in the image — those are "
            "added separately in layout. Each panel captures one beat of action or dialogue."
        ),
        "layout_visual": "comic_panels",
        "story_extra_rule": "Each page has 2-4 panels showing sequential moments. Story is action + dialogue driven. Use 'splash page' layout for dramatic moments and 'double spread' for epic wide moments.",
    },
    # ───────────────────────────────────────────────────────────────────
    {
        "id": "bold_board_book",
        "name": "Bold single-page board book",
        "emoji": "🧸",
        "badge": "Ages 0-3 top gift",
        "age_range": "0-3",
        "page_count": 8,
        "words_per_spread": "5-10",
        "total_words": "80-140",
        "trim_size": "6x6 in (square)",
        "text_placement": "centered_top_or_bottom",
        "font_size_pt": 28,
        "font_style": "ultra-bold display",
        "desc": "Bold images, tiny text, baby-friendly",
        "detail": "8 pages · 5-10 words per page · for toddlers",
        "bestsellers": ["Moo Baa La La La", "Brown Bear Brown Bear", "My First Animals"],
        "image_prompt_template": (
            "Bold children's board book illustration. Single subject {SUBJECT} centered on a "
            "solid bright color background. {ART_STYLE}. Ultra-thick black outlines, simple flat "
            "shapes, primary colors only. No small details — everything large, bold and recognizable. "
            "Maximum contrast. Suitable for infants 0-3."
        ),
        "layout_visual": "bold_board_book",
        "story_extra_rule": "Each page introduces ONE concept (one animal, one object, one action). Use repetition. Words a toddler knows. Sound effects: 'Moo!', 'Splash!'",
    },
]

# Default: most popular middle-of-the-road format
DEFAULT_FORMAT_ID = "illo_opposite_text"
DEFAULT_FORMAT = next(f for f in BOOK_FORMATS if f["id"] == DEFAULT_FORMAT_ID)


def get_format_by_id(fmt_id: str) -> dict:
    return next((f for f in BOOK_FORMATS if f["id"] == fmt_id), DEFAULT_FORMAT)


def get_page_count(fmt_id: str) -> int:
    return get_format_by_id(fmt_id)["page_count"]


def get_words_per_spread(fmt_id: str) -> str:
    return get_format_by_id(fmt_id)["words_per_spread"]


def get_image_template(fmt_id: str) -> str:
    return get_format_by_id(fmt_id)["image_prompt_template"]


def get_format_story_rules(fmt_id: str) -> str:
    """Return any format-specific story-writing rules (rhyming, dialogue, panels...)."""
    return get_format_by_id(fmt_id).get("story_extra_rule", "")


def get_layout_preview_html(fmt_id: str) -> str:
    """Return a small HTML preview showing the visual layout of the format."""
    layout = get_format_by_id(fmt_id).get("layout_visual", "illo_top_text_bottom")
    previews = {
        "illo_top_text_bottom": (
            '<div style="display:flex;gap:4px;">'
            '<div style="width:50%;aspect-ratio:1;background:linear-gradient(180deg,#a8c0ff 0%,#a8c0ff 70%,#fff 70%,#fff 100%);border-radius:4px;'
            'border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;bottom:8%;left:10%;right:10%;height:3px;background:#999;"></div>'
            '<div style="position:absolute;bottom:2%;left:25%;right:25%;height:3px;background:#999;"></div>'
            '</div>'
            '<div style="width:50%;aspect-ratio:1;background:linear-gradient(180deg,#ffd1a8 0%,#ffd1a8 70%,#fff 70%,#fff 100%);border-radius:4px;'
            'border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;bottom:8%;left:10%;right:10%;height:3px;background:#999;"></div>'
            '<div style="position:absolute;bottom:2%;left:25%;right:25%;height:3px;background:#999;"></div>'
            '</div>'
            '</div>'
        ),
        "full_bleed_double": (
            '<div style="aspect-ratio:2/1;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(255,255,255,0.3);"></div>'
            '<div style="position:absolute;bottom:10%;left:8%;right:60%;height:3px;background:rgba(255,255,255,0.7);"></div>'
            '<div style="position:absolute;bottom:4%;left:8%;right:65%;height:3px;background:rgba(255,255,255,0.7);"></div>'
            '</div>'
        ),
        "illo_opposite_text": (
            '<div style="display:flex;gap:4px;">'
            '<div style="width:50%;aspect-ratio:0.75;background:#a8c0ff;border-radius:4px;border:1px solid #ddd;"></div>'
            '<div style="width:50%;aspect-ratio:0.75;background:#fff;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:25%;left:10%;right:10%;height:3px;background:#999;"></div>'
            '<div style="position:absolute;top:35%;left:10%;right:15%;height:3px;background:#999;"></div>'
            '<div style="position:absolute;top:45%;left:10%;right:25%;height:3px;background:#999;"></div>'
            '<div style="position:absolute;top:55%;left:10%;right:10%;height:3px;background:#999;"></div>'
            '<div style="position:absolute;top:65%;left:10%;right:35%;height:3px;background:#999;"></div>'
            '</div>'
            '</div>'
        ),
        "rhyming_spread": (
            '<div style="display:flex;gap:4px;">'
            '<div style="width:50%;aspect-ratio:1.25;background:linear-gradient(180deg,#a8e6ff 0%,#a8e6ff 50%,#a8e6cf 100%);border-radius:4px;border:1px solid #ddd;'
            'position:relative;"><div style="position:absolute;top:30%;left:35%;width:30%;height:30%;background:#ff9aa2;border-radius:50%;"></div></div>'
            '<div style="width:50%;aspect-ratio:1.25;background:#fff;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:25%;left:15%;right:15%;height:4px;background:#666;"></div>'
            '<div style="position:absolute;top:32%;left:15%;right:25%;height:4px;background:#666;"></div>'
            '<div style="position:absolute;top:55%;left:15%;right:15%;height:4px;background:#666;"></div>'
            '<div style="position:absolute;top:62%;left:15%;right:30%;height:4px;background:#666;"></div>'
            '</div>'
            '</div>'
        ),
        "speech_bubble": (
            '<div style="display:flex;gap:4px;">'
            '<div style="width:50%;aspect-ratio:0.95;background:#fff8e7;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:55%;left:30%;width:40%;height:35%;background:#ff9aa2;border-radius:50% 50% 30% 30%;"></div>'
            '<div style="position:absolute;top:10%;left:25%;width:50%;height:30%;background:#fff;border:2px solid #333;border-radius:20px;"></div>'
            '</div>'
            '<div style="width:50%;aspect-ratio:0.95;background:#e7f8ff;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:55%;left:30%;width:40%;height:35%;background:#a8e6cf;border-radius:50% 50% 30% 30%;"></div>'
            '<div style="position:absolute;top:10%;left:25%;width:50%;height:30%;background:#fff;border:2px solid #333;border-radius:20px;"></div>'
            '</div>'
            '</div>'
        ),
        "spot_illustration": (
            '<div style="display:flex;gap:4px;">'
            '<div style="width:50%;aspect-ratio:0.75;background:#fff;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:8%;left:30%;width:40%;height:30%;background:#d4a574;border-radius:50%;"></div>'
            '<div style="position:absolute;top:42%;left:8%;right:8%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:48%;left:8%;right:15%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:54%;left:8%;right:8%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:60%;left:8%;right:25%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:66%;left:8%;right:8%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:72%;left:8%;right:18%;height:2px;background:#777;"></div>'
            '</div>'
            '<div style="width:50%;aspect-ratio:0.75;background:#fff;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:50%;left:30%;width:40%;height:30%;background:#7fa86e;border-radius:50%;"></div>'
            '<div style="position:absolute;top:10%;left:8%;right:8%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:16%;left:8%;right:18%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:22%;left:8%;right:8%;height:2px;background:#777;"></div>'
            '<div style="position:absolute;top:28%;left:8%;right:25%;height:2px;background:#777;"></div>'
            '</div>'
            '</div>'
        ),
        "comic_panels": (
            '<div style="display:flex;gap:4px;">'
            '<div style="width:50%;aspect-ratio:0.7;background:#fff;border-radius:4px;border:1px solid #ddd;display:flex;flex-direction:column;gap:2px;padding:3px;">'
            '<div style="flex:1;background:#ffb3a7;border:1px solid #333;"></div>'
            '<div style="flex:1;background:#a7d8ff;border:1px solid #333;"></div>'
            '</div>'
            '<div style="width:50%;aspect-ratio:0.7;background:#fff;border-radius:4px;border:1px solid #ddd;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:2px;padding:3px;">'
            '<div style="background:#fff3a7;border:1px solid #333;"></div>'
            '<div style="background:#a7ffb3;border:1px solid #333;"></div>'
            '<div style="background:#d4a7ff;border:1px solid #333;"></div>'
            '<div style="background:#ffd1a7;border:1px solid #333;"></div>'
            '</div>'
            '</div>'
        ),
        "bold_board_book": (
            '<div style="display:flex;gap:3px;">'
            '<div style="width:33%;aspect-ratio:1;background:#ff6b6b;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:25%;left:25%;width:50%;height:50%;background:#fff;border:3px solid #333;border-radius:50%;"></div>'
            '</div>'
            '<div style="width:33%;aspect-ratio:1;background:#4ecdc4;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:25%;left:25%;width:50%;height:50%;background:#ffd93d;border:3px solid #333;border-radius:50%;"></div>'
            '</div>'
            '<div style="width:33%;aspect-ratio:1;background:#ffd93d;border-radius:4px;border:1px solid #ddd;position:relative;">'
            '<div style="position:absolute;top:25%;left:25%;width:50%;height:50%;background:#ff6b6b;border:3px solid #333;border-radius:0;"></div>'
            '</div>'
            '</div>'
        ),
    }
    return previews.get(layout, previews["illo_top_text_bottom"])
