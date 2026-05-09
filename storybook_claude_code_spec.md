# Custom Storybook Generator — Claude Code Format Specification
# Based on: Top-selling children's books in India (Amazon.in + Flipkart, 2024–2025)
# Key insight: India's bestselling children's picture books are predominantly Western titles
# Top sellers: Very Hungry Caterpillar, Goodnight Moon, Where the Wild Things Are, 
#              The Gruffalo, Dr. Seuss series, Dog Man, Elephant & Piggie, Panchatantra collections

---

## CLAUDE CODE SYSTEM PROMPT

```
You are a custom children's storybook generator. Your job is:

1. Show the user the FORMAT SELECTION UI (load from bookFormats.json)
2. Collect story details (child name, age, theme, art style, language)
3. Generate a complete 32-page storybook in their chosen format

---

### STEP 1 — FORMAT PICKER UI

Render one card per format from bookFormats.json. Each card shows:
- Format name + bestseller badge
- Visual spread diagram (CSS layout preview — see render patterns below)
- Age range + words per spread
- 2–3 real bestselling books that use this format
- "Select this format" button

On select → reveal a detail panel showing full spec + AI image prompt template.

---

### STEP 2 — STORY DETAILS

Collect:
- Child's name (protagonist)
- Child's age: 1–2 / 3–4 / 5–6 / 7–8 / 9–10
- Story theme: Adventure / Friendship / Bedtime / Courage / Nature / Animals / Family / Moral fable
- Art style: Watercolor / Flat digital / Gouache / Colored pencil / Comic bold
- Language: English / Hindi / Tamil / Telugu / Bilingual (English + one regional)
- Optional: photo upload for character reference

---

### STEP 3 — GENERATE BOOK (32-page JSON output)

Return an array of 32 page objects:
{
  "page": 1,
  "spread_with": null,            // or page number if double spread
  "layout_type": "...",           // from format spec
  "story_text": "...",            // actual story text for this page
  "word_count": 14,
  "image_prompt": "...",          // full AI image generation prompt
  "text_placement": "...",        // where text sits on this page
  "page_notes": "..."             // pacing/mood note
}

Page structure (all 32-page formats):
- Page 1: Half-title (decorative, no story text)
- Page 2: Title page
- Page 3: Copyright + dedication
- Pages 4–29: Story (13 spreads)
- Pages 30–31: Resolution / ending
- Page 32: Blank (required for Amazon KDP print barcode)

---

### IMAGE PROMPT CONSTRUCTION RULES

Every image prompt must include ALL of these:
1. Art style (from user's selection)
2. Format-specific layout note (where text will appear — leave that zone clear)
3. Character consistency: "[Name] is a [age]-year-old [appearance], same on every page"
4. Mood/lighting for this specific spread
5. Color palette note
6. "No text in image" (always)
7. Print spec: "300 DPI, [trim size from format]"

Example:
"Watercolor children's book illustration. Arjun is a 5-year-old Indian boy with curly 
black hair and a yellow kurta, consistent throughout. Scene: Arjun feeding mangoes to 
a friendly elephant at sunset. Warm golden palette, soft watercolor textures. Leave 
bottom 30% as light ground/sky for text overlay. Gentle magical mood. No text in image. 
300 DPI, 8x8in square."
```

---

## BOOK FORMATS JSON (bookFormats.json)

```json
[
  {
    "id": "minimal_top_bottom",
    "name": "Illustration top, text bottom",
    "badge": "India + Global #1 bestseller",
    "age_range": "2–5",
    "words_per_spread": "8–15",
    "total_words": "150–250",
    "page_count": 32,
    "trim_size": "8x8 in (square)",
    "text_placement": "bottom_white_band",
    "text_band_pct": 30,
    "font_size_pt": 22,
    "font_style": "rounded bold sans-serif",
    "bestseller_refs": [
      "The Very Hungry Caterpillar — Eric Carle",
      "Goodnight Moon — Margaret Wise Brown",
      "Brown Bear Brown Bear — Bill Martin Jr"
    ],
    "india_context": "Consistently top-5 on Amazon.in children's category. Parents buy for toddlers. Very high repeat purchase rate.",
    "description": "Large illustration fills top 65–70% of page. Simple bold text in clean white space below. Maximum visual impact, minimum reading load.",
    "image_prompt_template": "Bold bright children's book illustration. [SCENE]. Large character fills top 70% of square page composition. Bottom 30% of image should fade to light/plain background — text will be placed here. [ART_STYLE]. High contrast, [PALETTE]. Simple expressive character. No text in image. 300 DPI, 8x8in.",
    "spread_sequence": [
      {"pages":"4–5","type":"double_spread_illo_text_bottom","note":"Opening — establish world"},
      {"pages":"6–29","type":"single_illo_top_text_bottom","note":"Story rhythm, one beat per page"},
      {"pages":"28–29","type":"double_spread_illo_text_bottom","note":"Climax moment"},
      {"pages":"30–31","type":"single_illo_top_text_bottom","note":"Warm ending"}
    ],
    "visual_layout_code": "illo_top_text_bottom"
  },

  {
    "id": "full_bleed_double",
    "name": "Full-bleed double spread",
    "badge": "Global bestseller",
    "age_range": "4–8",
    "words_per_spread": "20–40",
    "total_words": "350–550",
    "page_count": 32,
    "trim_size": "11x8.5 in (landscape)",
    "text_placement": "overlay_on_clear_area",
    "font_size_pt": 18,
    "font_style": "playful serif or hand-lettered",
    "bestseller_refs": [
      "Where the Wild Things Are — Maurice Sendak",
      "Dragons Love Tacos — Adam Rubin",
      "The Gruffalo — Julia Donaldson (key spreads)"
    ],
    "india_context": "Where the Wild Things Are is a consistent top-10 on Amazon.in. Parents buy for the dramatic artwork. Very popular as gift books.",
    "description": "Illustration spans both pages with no border. Text overlaid on a light/clear area of the illo. Grows in visual scale — quiet at start, full-bleed at climax, quiet at end.",
    "image_prompt_template": "Panoramic full-bleed children's book double spread. [SCENE]. [ART_STYLE]. Rich saturated colors. Leave [QUADRANT] area light (open sky or ground) for text overlay. Dramatic, [MOOD] lighting. No text in image. 300 DPI, 21x10in (full spread).",
    "pacing_rule": "Start with small illustrations on white pages, grow to full-bleed doubles at climax (pages 16–17), shrink back at ending — this is the Sendak technique that makes the story feel like it's literally expanding.",
    "spread_sequence": [
      {"pages":"4–5","type":"single_illo_wide_margins","note":"Quiet opening, small scene"},
      {"pages":"6–9","type":"single_full_bleed","note":"Story builds"},
      {"pages":"10–15","type":"double_spread_full_bleed","note":"Adventure grows"},
      {"pages":"16–17","type":"BIGGEST_double_spread","note":"CLIMAX — maximum bleed"},
      {"pages":"18–27","type":"alternating","note":"Resolution"},
      {"pages":"28–31","type":"single_illo_wide_margins","note":"Calm ending, mirrors opening"}
    ],
    "visual_layout_code": "full_bleed_double"
  },

  {
    "id": "illo_opposite_text",
    "name": "Full illustration opposite text page",
    "badge": "Classic literary bestseller",
    "age_range": "3–7",
    "words_per_spread": "25–50",
    "total_words": "300–600",
    "page_count": 32,
    "trim_size": "8.5x11 in (portrait)",
    "text_placement": "full_white_facing_page",
    "font_size_pt": 18,
    "font_style": "elegant serif or clean sans",
    "bestseller_refs": [
      "The Gruffalo — Julia Donaldson",
      "Green Eggs and Ham — Dr. Seuss",
      "Grandma's Bag of Stories — Sudha Murty"
    ],
    "india_context": "Sudha Murty's illustrated books use this format and are perennial Amazon.in bestsellers. Indian parents prefer this for the clean text — easy to read aloud.",
    "description": "Full illustration on one page, all text on the clean white facing page. Alternates which side each spread. Never crowded — the cleanest reading experience.",
    "image_prompt_template": "Full-page children's book illustration, portrait orientation. [SCENE]. Entire page is illustration — no text area needed. [ART_STYLE]. [PALETTE]. Story-advancing scene with expressive characters. 300 DPI, 8.5x11in.",
    "spread_sequence": [
      {"pages":"4–5","type":"illo_left_text_right","note":"Opening"},
      {"pages":"6–7","type":"text_left_illo_right","note":"Alternates"},
      {"pages":"8–27","type":"alternating","note":"Consistent alternation throughout"},
      {"pages":"28–29","type":"double_spread_exception","note":"One dramatic double spread at climax"},
      {"pages":"30–31","type":"illo_left_text_right","note":"Ending"}
    ],
    "visual_layout_code": "illo_opposite_text"
  },

  {
    "id": "rhyming_spread",
    "name": "Rhyming spread — illo left, verse right",
    "badge": "India top read-aloud",
    "age_range": "3–6",
    "words_per_spread": "12–20",
    "total_words": "200–300",
    "page_count": 32,
    "trim_size": "10x8 in (landscape)",
    "text_placement": "white_right_page_large_verse",
    "font_size_pt": 22,
    "font_style": "bold playful, varying sizes for emphasis",
    "rhyme_scheme": "AABB couplets or ABCB quatrains",
    "bestseller_refs": [
      "The Gruffalo — Julia Donaldson",
      "Pete the Cat — Eric Litwin",
      "Oh the Places You'll Go — Dr. Seuss"
    ],
    "india_context": "Rhyming books are the #1 read-aloud request from Indian parents. The Gruffalo is consistently top-selling on Amazon.in. Musical rhythm matches the way stories are traditionally told in Indian households.",
    "description": "Full-bleed illustration on left page; rhyming couplets or quatrains on clean white right page. The sing-song rhythm makes this the most-requested read-aloud format.",
    "image_prompt_template": "Full-bleed children's picture book left-page illustration, landscape orientation. [SCENE matching verse]. [ART_STYLE]. Expressive character, bold outlines, [PALETTE]. Full composition on left side — right page is separate white text page. No text in image. 300 DPI, 10x8in half-spread.",
    "spread_sequence": [
      {"pages":"4–5","type":"full_bleed_left_verse_right","note":"Opening verse sets scene"},
      {"pages":"6–25","type":"full_bleed_left_verse_right","note":"Verse by verse story"},
      {"pages":"16–17","type":"double_spread_text_overlay","note":"One big dramatic moment"},
      {"pages":"26–29","type":"full_bleed_left_verse_right","note":"Resolution verses"},
      {"pages":"30–31","type":"final_verse","note":"Satisfying rhyming ending"}
    ],
    "visual_layout_code": "rhyming_spread"
  },

  {
    "id": "speech_bubble",
    "name": "Speech bubble / dialogue-led",
    "badge": "Best for learning to read",
    "age_range": "4–7",
    "words_per_spread": "10–25",
    "total_words": "200–350",
    "page_count": 32,
    "trim_size": "8.5x9 in (portrait)",
    "text_placement": "speech_bubbles_above_characters",
    "font_size_pt": 20,
    "font_style": "bold rounded caps inside bubbles",
    "bestseller_refs": [
      "Elephant & Piggie series — Mo Willems",
      "Don't Let the Pigeon Drive the Bus — Mo Willems",
      "Tinkle Junior — ACK"
    ],
    "india_context": "Mo Willems books are strong sellers on Amazon.in in the 4–7 age bracket. The dialogue-only format helps Indian children learning English as their reading language.",
    "description": "Characters on white or solid backgrounds with large speech bubbles. Minimal background detail. Very large, expressive characters. Children track story through dialogue bubbles — ideal for first readers.",
    "image_prompt_template": "Simple children's book character illustration, white or flat [COLOR] background. [CHARACTER] with very expressive face and body language, large centered in frame. [ART_STYLE]. No background scenery — just the character. Flat digital style, big eyes, simple shapes. Leave space above head for speech bubble layout. No text or bubbles in image. 300 DPI, 8.5x9in.",
    "spread_sequence": [
      {"pages":"4–5","type":"two_characters_intro","note":"Meet both characters"},
      {"pages":"6–27","type":"dialogue_alternating","note":"Back and forth dialogue with action beats"},
      {"pages":"28–31","type":"resolution_dialogue","note":"Problem solved through conversation"}
    ],
    "visual_layout_code": "speech_bubble"
  },

  {
    "id": "spot_illustration",
    "name": "Spot illustration with flowing text",
    "badge": "Panchatantra / fable style",
    "age_range": "5–9",
    "words_per_spread": "40–70",
    "total_words": "600–900",
    "page_count": 32,
    "trim_size": "8.5x11 in (portrait)",
    "text_placement": "around_and_below_vignette",
    "font_size_pt": 16,
    "font_style": "elegant serif, classic literary",
    "bestseller_refs": [
      "Panchatantra collections (perennial #1 in India)",
      "Grandma's Bag of Stories — Sudha Murty",
      "If You Give a Mouse a Cookie — Laura Numeroff"
    ],
    "india_context": "Panchatantra and Jataka Tales collections are perennial bestsellers in India. The spot illustration format is the dominant style for Indian moral story books and is deeply familiar to Indian parents.",
    "description": "Circular or vignette spot illustrations float in generous white space surrounded by story text. Multiple small scenes per page possible. Classic, timeless, literary feel.",
    "image_prompt_template": "Spot illustration for children's fable, vignette style. [SCENE with animal characters]. Circular or irregular vignette composition — white/transparent background outside the main scene area. [ART_STYLE]. Warm earthy colors. Animals with expressive human emotions. Classic storybook style. 300 DPI, spot size approx 4x4in.",
    "spread_sequence": [
      {"pages":"4–5","type":"full_bleed_chapter_opener","note":"Dramatic opening scene"},
      {"pages":"6–27","type":"spot_illo_with_text","note":"Story paragraphs with spot illustrations"},
      {"pages":"28–29","type":"full_bleed_resolution","note":"Resolution scene"},
      {"pages":"30–31","type":"moral_page","note":"Moral of the story with decorative border"}
    ],
    "visual_layout_code": "spot_illustration"
  },

  {
    "id": "comic_panels",
    "name": "Comic panel grid",
    "badge": "India icon — ACK + Dog Man",
    "age_range": "6–12",
    "words_per_spread": "40–80",
    "total_words": "700–1200",
    "page_count": 32,
    "trim_size": "7x10 in (portrait)",
    "text_placement": "speech_bubbles_and_caption_boxes",
    "font_size_pt": 14,
    "font_style": "bold comic rounded caps",
    "panel_layouts": ["2_panel_vertical","3_panel_row","4_panel_grid","1_full_page_splash","double_spread_panorama"],
    "bestseller_refs": [
      "Amar Chitra Katha (100M+ sold in India)",
      "Dog Man series — Dav Pilkey",
      "Diary of a Wimpy Kid — Jeff Kinney"
    ],
    "india_context": "Amar Chitra Katha is India's most-sold children's book series ever. Dog Man is consistently top-10 on Amazon.in for ages 6–10. Comic format drives the highest engagement from reluctant readers.",
    "description": "2–4 sequential panels per page with speech bubbles and caption boxes. Great for mythology, adventure, and fables. The format of India's most beloved children's brand.",
    "image_prompt_template": "Single comic panel illustration for children's book. [ACTION/DIALOGUE MOMENT]. [ART_STYLE]. Thick black outlines, dynamic character pose, expressive face. [PALETTE: jewel tones / bright flat]. No speech bubbles or text in image — those are added in layout. Ages 6–12. 300 DPI, panel size varies.",
    "panel_guide": {
      "dialogue_scene": "2_panel_vertical — character A left, character B right",
      "action_sequence": "3_panel_row — setup, action, reaction",
      "fast_paced": "4_panel_grid — quick cuts",
      "dramatic_reveal": "1_full_page_splash — chapter opener or climax",
      "epic_moment": "double_spread_panorama — battle, celebration, grand vista"
    },
    "spread_sequence": [
      {"pages":"4","type":"full_page_splash","note":"Opening splash — establish hero"},
      {"pages":"5–15","type":"3_or_4_panel","note":"Setup and inciting incident"},
      {"pages":"16–17","type":"double_spread_panorama","note":"First major action beat"},
      {"pages":"18–27","type":"3_or_4_panel","note":"Rising action + climax panels"},
      {"pages":"28–29","type":"full_page_splash","note":"Climax resolution"},
      {"pages":"30–31","type":"2_panel","note":"Denouement + moral"}
    ],
    "visual_layout_code": "comic_panels"
  },

  {
    "id": "bold_board_book",
    "name": "Bold single-page board book",
    "badge": "Ages 0–3 top gift",
    "age_range": "0–3",
    "words_per_spread": "5–10",
    "total_words": "80–140",
    "page_count": 14,
    "trim_size": "6x6 in (square)",
    "text_placement": "centered_top_or_bottom",
    "font_size_pt": 28,
    "font_style": "ultra-bold display",
    "bestseller_refs": [
      "Moo Baa La La La — Sandra Boynton",
      "Brown Bear Brown Bear — Bill Martin Jr",
      "My First Animals (board book)"
    ],
    "india_context": "Board books are the #1 gifting item for babies 0–3 on Amazon.in. High repeat purchase. Parents and grandparents buy multiple sets. Simple bold format transcends language barriers.",
    "description": "One bold illustration per page. 1–2 very short sentences or a single large label. Ultra-thick outlines, maximum contrast, solid primary colors. Everything large and recognizable.",
    "image_prompt_template": "Bold children's board book illustration. Single subject [ANIMAL/OBJECT/CHARACTER] centered on solid [COLOR] background. Ultra-thick black outlines, simple flat shapes, primary colors only. No small details — everything large, bold, recognizable. Maximum contrast. [LABEL TEXT area at bottom if needed]. Suitable for infants 0–3. 300 DPI, 6x6in square.",
    "spread_sequence": [
      {"pages":"2–3","type":"concept_intro","note":"First character/concept"},
      {"pages":"4–11","type":"repeating_concept","note":"Each spread = one new object/animal/sound"},
      {"pages":"12–13","type":"all_together","note":"All characters or summary spread"}
    ],
    "visual_layout_code": "bold_board_book"
  }
]
```

---

## RENDER LOGIC FOR FORMAT PICKER UI

Each format card needs a visual spread preview. Here is the CSS layout pattern for each `visual_layout_code`:

```
"illo_top_text_bottom"
  → Two page cards side by side
  → Each: colored top 70% (illustration area) + white bottom 30% with text lines

"full_bleed_double"
  → One wide card spanning both pages
  → Full color background + gutter line in center + text lines bottom-left

"illo_opposite_text"
  → Two page cards side by side
  → Left: full color illustration
  → Right: white with centered text lines

"rhyming_spread"
  → Two page cards side by side
  → Left: full color illustration (sky top, ground bottom, character center)
  → Thin gutter
  → Right: white with two couplet groups (4 lines with gap between)

"speech_bubble"
  → Two page cards side by side
  → Each: white/solid bg + centered character shape + speech bubble above

"spot_illustration"
  → Two page cards side by side
  → Each: white bg + circle in center top + text lines below

"comic_panels"
  → Two page cards side by side
  → Left: 2 panels stacked (2×1 grid)
  → Right: 4 panels (2×2 grid)
  → Each panel has a small character silhouette

"bold_board_book"
  → Three mini page cards
  → Each: solid primary color bg + bold circle/shape + single text line
```

---

## IMPLEMENTATION NOTES FOR CLAUDE CODE

### User flow:
```
App loads → Show format picker grid (8 cards)
         → User clicks card → Detail panel expands below
         → User clicks "Use this format" → Go to story form
         → Story form submitted → Generate 32-page JSON
         → Render book preview page by page
         → Export options (PDF / images + prompts / print-ready)
```

### Key rules for story generation:
- Respect `words_per_spread` strictly — never exceed max
- Use `spread_sequence` to assign correct layout type to each page
- Insert Indian/culturally resonant detail naturally if child's name is Indian
- Page 32 is always blank — do not write story content for it
- Right-hand pages should end on tension/question/incomplete action (drives page turns)
- Character description must be identical in every image prompt

---
*India market research: Amazon.in children's bestseller lists 2024–2025, Flipkart children's category, Kidsstoppress.com curated lists. Top sellers are predominantly Western titles (Eric Carle, Sendak, Dr. Seuss, Mo Willems, Dav Pilkey) plus Sudha Murty and Panchatantra/ACK collections.*
