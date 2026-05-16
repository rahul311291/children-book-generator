# ========================================================================
# STORY PROMPTS CONFIGURATION FILE
# ========================================================================
# This file contains all prompts for different age groups.
# Edit this file directly to change how stories are generated.
#
# HOW TO EDIT:
# - Each age group has its own section below
# - Edit the text between the triple quotes
# - Use {child_name}, {age}, {gender}, etc. as placeholders - they get replaced automatically
# - Save the file and restart the app to see changes
#
# AVAILABLE PLACEHOLDERS:
# - {child_name} = The child's name
# - {age} = The child's age
# - {gender} = The child's gender
# - {family_info} = Family structure description
# - {hero_trait} = The child's strength/trait
# - {story_theme} = The story theme/problem provided by parent
# - {language} = English or Hindi
# - {character_companion} = Famous character if any (Max and Mini, Peppa Pig, etc.)
# ========================================================================

# ============================================================================
# AGE GROUP: 2-3 YEARS (Toddlers)
# ============================================================================
AGE_2_3_PROMPT = """
You are creating a picture book for a TODDLER aged 2-3 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{character_companion}

RULES FOR 2-3 YEAR OLDS:
1. EXTREMELY SIMPLE LANGUAGE:
   - Maximum 1 sentence per page (5-8 words)
   - Use only words a toddler knows: mama, papa, ball, cat, dog, eat, sleep, play
   - Repeat key words for familiarity
   - Simple sounds: "Woof! Woof!", "Yum yum!", "Splash!"
   
2. STORY STRUCTURE (8 pages only):
   - Page 1-2: Introduce {child_name} doing something happy
   - Page 3-4: Something simple happens (a ball rolls, a cat appears)
   - Page 5-6: {child_name} interacts with it
   - Page 7-8: Happy ending with cuddles/smiles
   
3. VISUAL REQUIREMENTS:
   - BIG, BOLD images with few elements
   - Bright primary colors only (red, blue, yellow, green)
   - One main action per page
   - Large, friendly faces showing emotions clearly
   - NO busy backgrounds - solid colors or very simple settings

4. THEMES THAT WORK FOR 2-3:
   - Everyday routines (eating, sleeping, bath time)
   - Animals and sounds they make
   - Family love and cuddles
   - Simple objects (ball, teddy, shoes)
   
5. AVOID:
   - Complex plots or problems
   - Scary elements (even mild)
   - Abstract concepts
   - More than 2 characters per scene
"""

# ============================================================================
# AGE GROUP: 3-4 YEARS (Pre-Nursery)
# ============================================================================
AGE_3_4_PROMPT = """
You are creating a picture book for a child aged 3-4 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{character_companion}

RULES FOR 3-4 YEAR OLDS:
1. SIMPLE LANGUAGE:
   - 1-2 short sentences per page (8-12 words total)
   - Use familiar words with some new vocabulary
   - Rhymes and repetition work great: "Run, run, run! Fun, fun, fun!"
   - Sound effects: "Whoooosh!", "Splat!", "Ding dong!"
   
2. STORY STRUCTURE (8-10 pages):
   - Page 1-2: {child_name} in their world, happy
   - Page 3-4: A small challenge or something new appears
   - Page 5-6: {child_name} tries to solve it (simple attempts)
   - Page 7-8: Solution found with help from family/friend
   - Page 9-10: Celebration and happy ending
   
3. VISUAL REQUIREMENTS:
   - Clear, colorful illustrations
   - 2-3 characters maximum per scene
   - Show emotions clearly on faces
   - Simple backgrounds (home, park, garden)
   - Action should be obvious from the image alone

4. THEMES THAT WORK FOR 3-4:
   - Making friends
   - Sharing toys
   - Trying new foods
   - Going to playschool
   - Helping at home
   - Animals and nature
   - Simple adventures
   
5. EMOTIONAL LEARNING:
   - Name basic emotions: happy, sad, scared, angry
   - Show that it's okay to feel feelings
   - Adults help when needed
"""

# ============================================================================
# AGE GROUP: 4-5 YEARS (Nursery/KG1)
# ============================================================================
AGE_4_5_PROMPT = """
You are creating a picture book for a child aged 4-5 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{hero_trait}
{character_companion}

RULES FOR 4-5 YEAR OLDS:
1. LANGUAGE:
   - 2-3 sentences per page
   - Introduce new vocabulary with context
   - Use dialogue: "{child_name} said, 'I can do it!'"
   - Rhymes, songs, and catchy phrases
   
2. STORY STRUCTURE (10 pages):
   - Page 1-2: Introduction - {child_name}'s world and the setup
   - Page 3-4: The challenge/problem appears
   - Page 5-6: First attempt - it doesn't work
   - Page 7-8: {child_name} thinks and tries again
   - Page 9: Success!
   - Page 10: Resolution with lesson learned naturally
   
3. VISUAL REQUIREMENTS:
   - Detailed but not overwhelming illustrations
   - Show sequence of actions
   - Include things to find/count in images
   - Expressive characters
   - Varied settings (home, school, park, etc.)

4. CAN INCLUDE SIMPLE ACTIVITIES:
   - "Can you find the red ball in the picture?"
   - "Count how many butterflies!"
   - "What sound does this animal make?"
   
5. THEMES THAT WORK FOR 4-5:
   - Overcoming fears (dark, dogs, new places)
   - Making friends at school
   - Being brave
   - Helping others
   - Simple problem-solving
   - Curiosity and asking "why"
   
6. EMOTIONAL DEPTH:
   - {child_name} can feel frustrated, then proud
   - Show that trying is important
   - {child_name} can solve problems (with some help)
"""

# ============================================================================
# AGE GROUP: 5-6 YEARS (KG2/Prep)
# ============================================================================
AGE_5_6_PROMPT = """
You are creating a picture book for a child aged 5-6 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{hero_trait}
{character_companion}

RULES FOR 5-6 YEAR OLDS:
1. LANGUAGE:
   - 3-4 sentences per page
   - Richer vocabulary with explanations woven in
   - More dialogue between characters
   - Descriptive words: "the sparkly, magical wand"
   
2. STORY STRUCTURE (10-12 pages):
   - Beginning: Set the scene, introduce characters
   - Problem: Clear challenge that {child_name} must overcome
   - Middle: Multiple attempts, learning from failures
   - Climax: The big moment of bravery/cleverness
   - Resolution: Happy ending with reflection
   
3. VISUAL REQUIREMENTS:
   - Rich, detailed illustrations
   - Multiple scenes can be shown (panels/sequence)
   - Include visual storytelling details
   - Interactive elements in images
   - Diverse settings

4. ACTIVITIES TO INCLUDE:
   - "What do you think happens next?"
   - "Match the tool to the task" (simple mapping)
   - "Circle the odd one out"
   - Simple mazes
   - "Draw what {child_name} found"
   
5. THEMES THAT WORK FOR 5-6:
   - Responsibility and taking care of things
   - Teamwork and cooperation
   - Dealing with mistakes
   - Imagination and creativity
   - Learning new skills
   - Empathy for others
   
6. THE CHILD AS HERO:
   - {child_name} solves the problem themselves
   - Adults guide but don't solve for them
   - Natural consequences shown
   - Pride in achievement
"""

# ============================================================================
# AGE GROUP: 6-7 YEARS (Grade 1)
# ============================================================================
AGE_6_7_PROMPT = """
You are creating a storybook for a child aged 6-7 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{hero_trait}
{character_companion}

RULES FOR 6-7 YEAR OLDS:
1. LANGUAGE:
   - 4-5 sentences per page
   - Chapter-like sections possible
   - Rich dialogue and character thoughts
   - Introduce challenging words with context clues
   - Some humor and wordplay
   
2. STORY STRUCTURE (12-14 pages):
   - Clear beginning, middle, end
   - Subplots possible (a friend helps, learns something too)
   - Twists and surprises
   - {child_name} shows growth throughout
   
3. VISUAL REQUIREMENTS:
   - Can include more complex scenes
   - Show passage of time
   - Include details that reward close looking
   - Mix of action and quiet moments
   - Can include maps, diagrams for adventure stories

4. ACTIVITIES (More Complex):
   - "What would YOU do in this situation?"
   - Simple word puzzles related to story
   - Mapping exercises (if story involves journey)
   - "Write what happens next"
   - Character comparison charts
   
5. THEMES THAT WORK FOR 6-7:
   - Fairness and justice
   - Standing up for yourself/others
   - Dealing with change
   - Competition and sportsmanship
   - Learning from mistakes
   - Environmental awareness
   - Friendship conflicts and resolution

6. CHARACTER DEVELOPMENT:
   - {child_name} has clear personality traits
   - Shows growth and change
   - Faces internal and external challenges
   - Makes decisions with consequences
"""

# ============================================================================
# AGE GROUP: 7-8 YEARS (Grade 2)
# ============================================================================
AGE_7_8_PROMPT = """
You are creating a chapter-style storybook for a child aged 7-8 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{hero_trait}
{character_companion}

RULES FOR 7-8 YEAR OLDS:
1. LANGUAGE:
   - 5-6 sentences per page
   - Can organize into chapters
   - Complex sentences with "because", "although", "however"
   - Character's internal thoughts shown
   - Varied sentence structures
   
2. STORY STRUCTURE (14-16 pages):
   - Multi-layered plot
   - Red herrings and surprises
   - Multiple characters with their own motivations
   - {child_name} as the clear protagonist
   - Satisfying resolution that ties threads together
   
3. VISUAL REQUIREMENTS:
   - Illustrations support but don't tell the whole story
   - Can include thought bubbles, flashbacks
   - Maps for adventure stories
   - Before/after comparisons
   - Character expression sheets

4. ACTIVITIES (Engaging):
   - Prediction exercises
   - Character motivation analysis
   - Story mapping activities
   - Creative writing prompts
   - Compare/contrast exercises
   - Vocabulary building games
   
5. THEMES THAT WORK FOR 7-8:
   - Perseverance and grit
   - Leadership and responsibility
   - Complex friendships
   - Dealing with peer pressure
   - Discovery and investigation
   - Moral dilemmas (age-appropriate)
   - Different perspectives on same event

6. DEPTH:
   - Show that problems aren't always simple
   - Multiple solutions possible
   - Actions have consequences
   - Others have feelings too
"""

# ============================================================================
# AGE GROUP: 8-10 YEARS (Grade 3-4)
# ============================================================================
AGE_8_10_PROMPT = """
You are creating an illustrated chapter book for a child aged 8-10 years.

STORY FOR: {child_name} (Age: {age}, Gender: {gender})
THEME/IDEA: {story_theme}
LANGUAGE: {language}
{family_info}
{hero_trait}
{character_companion}

RULES FOR 8-10 YEAR OLDS:
1. LANGUAGE:
   - 6-8 sentences per page
   - Chapter format with cliffhangers
   - Sophisticated vocabulary
   - Dialogue-driven narrative
   - First-person or close third-person narration
   - Internal monologue
   
2. STORY STRUCTURE (16-20 pages):
   - Strong opening hook
   - Rising action with escalating stakes
   - Complex character relationships
   - Plot twists that make sense
   - Climax that requires {child_name} to change or grow
   - Denouement that reflects on the journey
   
3. VISUAL REQUIREMENTS:
   - Illustrations at key moments
   - Can be more stylized or artistic
   - Include maps, diagrams, artifacts
   - Visual breaks in text-heavy sections
   - Character design consistency

4. ACTIVITIES (Challenge Level):
   - Critical thinking questions
   - "What if" scenarios
   - Story extension writing
   - Character diary entries
   - Research tie-ins (for educational themes)
   - Debate topics from the story
   - Create your own ending
   
5. THEMES THAT WORK FOR 8-10:
   - Identity and self-discovery
   - Justice vs. rules
   - Complex family dynamics
   - Environmental/social issues (age-appropriate)
   - Historical or futuristic settings
   - Mystery and detective work
   - Fantasy and world-building
   - Real-world challenges (moving, divorce, loss - handled sensitively)

6. READER AS THINKER:
   - Don't spell everything out
   - Let reader draw conclusions
   - Ambiguity is okay in places
   - Multiple valid interpretations
   - Encourage discussion
"""

# ============================================================================
# COMMON VISUAL CONSISTENCY RULES (Applied to ALL ages)
# ============================================================================
VISUAL_CONSISTENCY_RULES = """
VISUAL CONSISTENCY RULES:

1. CHARACTER APPEARANCE (for close-up / interaction pages):
   - Create a 'Visual Anchor' that describes {child_name} exactly
   - Include: age, gender, skin tone, hair color/style, eye color, ONE consistent outfit
   - Use this EXACT description on every page where {child_name} is the focus
   - NEVER change the outfit, hairstyle, or features between pages

2. SCENE-FOCUSED PAGES (grand vistas, crowds, events, panoramas):
   - Use image_type = "scene" for these pages
   - {child_name} may appear SMALL in the scene, as one figure among many
   - Do NOT make {child_name} the visual centre of a scene page
   - The crowd, environment, event, or spectacle IS the subject
   - Example: an Olympic arena filled with hundreds of animals — {child_name} is a
     small figure watching from the stands or participating in a crowd

3. CHARACTER CLOSE-UP PAGES:
   - Use image_type = "character" for these pages
   - {child_name} fills most of the frame; scene is supporting background
   - Full visual_anchor description required

4. FAMOUS CHARACTER COMPANION (Only if specified):
   - If {character_companion} is provided, include them in relevant pages
   - They should have dialogue and appear in illustrations
"""

# ============================================================================
# JSON OUTPUT FORMAT (Same for all ages)
# ============================================================================
OUTPUT_FORMAT = """
OUTPUT FORMAT (Return as JSON only):

{{
  "title": "Creative title using the EXACT name '{child_name}' if relevant",
  "visual_anchor": "Concise consistent appearance of {child_name}: age, gender, skin tone, hair, eye color, ONE specific outfit. ~25 words. Used on character-focused pages only.",
  "pages": [
    {{
      "page_number": 1,
      "text": "Story text for this page (use exact name '{child_name}')",
      "shot_type": "ONE OF: wide_establishing | aerial_panorama | crowd_ensemble | action_dynamic | mid_shot_character | close_up_emotion | montage_sequence | environment_only",
      "primary_subject": "ONE short sentence stating WHAT THIS IMAGE PRIMARILY SHOWS. For scene shots this is the environment/event/crowd, NOT the protagonist.",
      "visual_description": "RICH 3-5 sentence cinematic description following the structure in the rules below."
    }}
  ]
}}

═══════════════════════════════════════════════════════════════════════════
HOW TO WRITE visual_description (THE MOST IMPORTANT PART)
═══════════════════════════════════════════════════════════════════════════

Required structure for EVERY visual_description:

  Sentence 1: SHOT TYPE + PRIMARY SUBJECT
    e.g. "Wide cinematic establishing shot of a vast jungle clearing transformed
         into an arena, packed with thousands of cheering animals."

  Sentence 2: ENVIRONMENT / SETTING DETAILS
    e.g. "Bamboo grandstands rise on three sides, draped with banners of leaves
         and flowers; golden afternoon sunlight streams through the canopy above."

  Sentence 3: SPECIFIC ACTION / WHAT IS HAPPENING
    e.g. "On the central track a lion is mid-sprint, a kangaroo bounds alongside
         a cheetah, and a giraffe gallops in long strides — all racing for the finish line."

  Sentence 4: CHARACTER PLACEMENT (only if relevant)
    For shot_type=wide_establishing/aerial_panorama/crowd_ensemble/environment_only:
      Either omit, or write: "{child_name} appears as a tiny figure in the stands,
      one wide-eyed onlooker among hundreds."
    For shot_type=mid_shot_character/close_up_emotion:
      Write the full visual_anchor here: "{child_name} stands in the foreground —
      [paste visual_anchor word-for-word]."
    For shot_type=action_dynamic:
      Write a brief mention: "{child_name} ([brief 5-word descriptor]) is in motion."

  Sentence 5: ATMOSPHERE / MOOD / LIGHTING / COLOR PALETTE
    e.g. "Dust rises from the track, flags snap in the breeze, the mood is
         electric and triumphant — bold saturated colors, dynamic motion lines."

═══════════════════════════════════════════════════════════════════════════
SHOT TYPE GUIDE
═══════════════════════════════════════════════════════════════════════════

  wide_establishing  - Sets the scene: location, scale, what world we're in
  aerial_panorama    - Bird's eye view; shows extent of environment/crowd
  crowd_ensemble     - Many characters together; protagonist NOT singled out
  action_dynamic     - Mid-action with motion blur, bold poses, energy
  mid_shot_character - Protagonist waist-up doing something specific
  close_up_emotion   - Face / hands / object close-up; emotional moment
  montage_sequence   - Multiple small images in one frame (e.g. 4 different
                       competitors trying the same sport)
  environment_only   - Pure scene/object/place with NO characters (transitions)

═══════════════════════════════════════════════════════════════════════════
VARIETY MANDATE (HARD REQUIREMENT)
═══════════════════════════════════════════════════════════════════════════

Across the book:
  - Use AT LEAST 5 different shot_type values
  - Never use the same shot_type for 3 pages in a row
  - Open with wide_establishing or aerial_panorama (set the world)
  - Climactic moments → action_dynamic or crowd_ensemble (NOT character close-ups)
  - End with a mid_shot_character or close_up_emotion (resolution feels personal)

For STORIES INVOLVING crowds, events, journeys, gatherings, competitions, festivals:
  - At least 60% of pages must be scene-focused (wide_establishing,
    aerial_panorama, crowd_ensemble, action_dynamic, montage_sequence,
    or environment_only)
  - The visual richness of the EVENT is the star — don't waste pages on
    static character portraits

For QUIET / INTIMATE / PERSONAL stories:
  - Mix close_up_emotion, mid_shot_character, environment_only, wide_establishing
  - One or two action_dynamic moments at the climax

═══════════════════════════════════════════════════════════════════════════
GOOD vs BAD EXAMPLES
═══════════════════════════════════════════════════════════════════════════

❌ BAD (character-centric, ignores plot scale):
   "{child_name}, a 6-year-old girl with brown hair in a yellow dress, stands
   smiling. She is at a sports event."

✓ GOOD (scene-focused, plot-specific):
   "Wide cinematic shot of an enormous outdoor sports arena carved from a
   hillside, the curved bamboo stands rising into the misty mountains.
   Hundreds of jungle creatures fill every seat, a lion conductor raising
   his paw to signal the start of the games. {child_name} appears as a small
   figure in the front row, eyes wide. Late afternoon light rakes across the
   field, banners snap in the breeze."

❌ BAD (vague, no shot direction):
   "An action scene where animals compete. {child_name} cheers."

✓ GOOD (explicit, dynamic, multi-figure):
   "Dynamic action shot at ground level: the dirt track exploding with motion
   as a kangaroo, a tiger, an antelope and a gorilla all sprint toward the
   camera, dust kicked up in golden afternoon light. Stadium crowd a blur of
   color in the background. {child_name} is among the runners, second from left,
   pumping her arms. Energy radiates outward — this is the climactic race."

═══════════════════════════════════════════════════════════════════════════

CRITICAL: Output ONLY valid JSON. No extra text before or after.
"""

# ============================================================================
# FUNCTION TO GET PROMPT BY AGE
# ============================================================================
def get_prompt_for_age(age: int) -> str:
    """Return the appropriate prompt based on child's age."""
    if age <= 3:
        return AGE_2_3_PROMPT
    elif age == 4:
        return AGE_3_4_PROMPT
    elif age == 5:
        return AGE_4_5_PROMPT
    elif age == 6:
        return AGE_5_6_PROMPT
    elif age == 7:
        return AGE_6_7_PROMPT
    elif age == 8:
        return AGE_7_8_PROMPT
    else:  # 9-10+
        return AGE_8_10_PROMPT

def get_full_prompt(age: int, child_name: str, gender: str, story_theme: str,
                    language: str, family_info: str = "", hero_trait: str = "",
                    character_companion: str = "", story_type: str = "",
                    book_format: dict = None) -> str:
    """Build the complete prompt with all placeholders filled in."""

    # ── NAME LOCK (CRITICAL) ────────────────────────────────────────────────
    # Some models silently rename the child if the name resembles a famous
    # character (Elsa, Anna, Harry...). This block forces exact preservation.
    name_lock = f"""
=== NAME LOCK (ABSOLUTE RULE) ===
The child's name is EXACTLY: {child_name}

You MUST use this exact spelling on every page, in the title, and in every
visual_description. NEVER:
  - Substitute it with a similar-sounding name
  - Change it because it matches a Disney/Pixar/published character
  - Add nicknames, pet names, or alternative spellings
  - Translate it to another language

The story is for THIS specific real child named "{child_name}". The name is
not a copyright concern — the child's parent typed it themselves. Use it as-is.
=== END NAME LOCK ===
"""

    # ── PLOT-FIRST BLOCK ────────────────────────────────────────────────────
    story_type_line = f"STORY TYPE: {story_type}" if story_type else ""
    plot_anchor = f"""
=== THE STORY YOU MUST TELL (HIGHEST PRIORITY) ===
The parent has described exactly what they want. Build the entire story around this:

  "{story_theme}"

{story_type_line}

THIS IS NOT A SUGGESTION. Every page, every scene, every image description must
serve THIS specific plot. Do not replace it with a generic story about the same
topic. If the parent says "Arjun discovers a magic door in the park", the story
is about that magic door — not a generic adventure.

The age-appropriate rules below govern LANGUAGE and STRUCTURE only — they do not
override or replace this story. Adapt the structure to fit the plot.
=== END PLOT ANCHOR ===
"""

    # ── BOOK FORMAT BLOCK ───────────────────────────────────────────────────
    format_block = ""
    if book_format:
        page_count = book_format.get("page_count", 10)
        words_per = book_format.get("words_per_spread", "30-50")
        extra = book_format.get("story_extra_rule", "")
        extra_line = f"\nFORMAT-SPECIFIC RULE: {extra}" if extra else ""
        format_block = f"""
=== BOOK FORMAT ===
This book follows the "{book_format.get('name')}" format:
  - EXACTLY {page_count} pages (do not return more or fewer)
  - {words_per} words per page
  - Bestseller examples in this format: {', '.join(book_format.get('bestsellers', [])[:3])}{extra_line}
=== END BOOK FORMAT ===
"""

    # Get age-appropriate prompt
    base_prompt = get_prompt_for_age(age)

    # Format placeholders
    family_text = f"FAMILY CONTEXT: {family_info}" if family_info else ""
    hero_text = f"HERO TRAIT (use to help solve the plot): {hero_trait}" if hero_trait else ""
    character_text = (
        f"FAMOUS CHARACTER COMPANION: Include {character_companion} as a friend in this story "
        f"with dialogue. They appear in images too."
        if character_companion else ""
    )

    prompt = base_prompt.format(
        child_name=child_name, age=age, gender=gender, story_theme=story_theme,
        language=language, family_info=family_text, hero_trait=hero_text,
        character_companion=character_text,
    )

    visual_rules = VISUAL_CONSISTENCY_RULES.format(
        child_name=child_name,
        character_companion=character_companion if character_companion else "N/A",
    )

    output = OUTPUT_FORMAT.format(child_name=child_name)

    # Order matters: NAME LOCK > PLOT > FORMAT > age rules > visual rules > output spec
    return name_lock + "\n\n" + plot_anchor + "\n\n" + format_block + "\n\n" + prompt + "\n\n" + visual_rules + "\n\n" + output


# ============================================================================
# IMAGE STYLE DESCRIPTIONS
# ============================================================================
IMAGE_STYLES = {
    "Cartoon/Animated (3D Pixar Style)": "3D Pixar style animation, vibrant colors, soft lighting, children's book art, high quality, detailed, cute cartoon characters",
    "Cartoon (2D Flat Style)": "2D flat cartoon style, bold outlines, bright colors, simple shapes, children's book illustration, clean vector art style",
    "Photorealistic": "Photorealistic photograph, highly detailed, natural lighting, realistic textures, professional photography, lifelike human figures, real-world setting",
    "Watercolor Illustration": "Watercolor painting style, soft edges, gentle colors, artistic brushstrokes, traditional illustration, dreamy aesthetic",
    "Storybook Classic": "Classic storybook illustration, warm colors, nostalgic feel, traditional children's book art, hand-drawn style, detailed backgrounds",
    "Photo Reference Portrait": (
        "Semi-realistic children's storybook portrait illustration. Painterly watercolor-meets-photography style. "
        "The child's face is rendered with photographic accuracy: exact facial structure, eye shape and color, "
        "skin tone, hair color and texture, nose, lips — all precisely matching the reference photo. "
        "Professional portrait quality. Warm studio lighting. Soft painterly background. "
        "The child is recognisable to their own parents in every illustration."
    ),
}

def get_image_style(style_name: str) -> str:
    """Return the image style modifiers for the selected style."""
    return IMAGE_STYLES.get(style_name, IMAGE_STYLES["Cartoon/Animated (3D Pixar Style)"])

