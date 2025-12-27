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
VISUAL CONSISTENCY (CRITICAL - Apply to ALL ages):

1. CHARACTER APPEARANCE:
   - Create a 'Visual Anchor' that describes {child_name} exactly
   - Include: age, gender, skin tone, hair color/style, eye color, ONE consistent outfit
   - This EXACT description must appear in EVERY image prompt
   - NEVER change the outfit, hairstyle, or features between pages
   
2. OUTFIT RULE:
   - Pick ONE outfit at the start
   - If parent provided "favorite outfit", use exactly that
   - If not, choose simple clothing (e.g., "red t-shirt and blue jeans")
   - Use IDENTICAL outfit description word-for-word on every page
   
3. HAIRSTYLE RULE:
   - Describe hairstyle specifically: "curly black hair in two ponytails"
   - NEVER change hairstyle between pages
   - Use the same description every time
   
4. FAMOUS CHARACTER COMPANION (Only if specified):
   - If {character_companion} is provided, include that character in the story
   - They should have dialogue and appear in illustrations
   - They help {child_name} but don't solve everything for them
"""

# ============================================================================
# JSON OUTPUT FORMAT (Same for all ages)
# ============================================================================
OUTPUT_FORMAT = """
OUTPUT FORMAT (Return as JSON only):

{{
  "title": "Creative Story Title",
  "visual_anchor": "Complete description of {child_name} - age, gender, skin tone, hair (style + color), eyes, outfit. This EXACT description appears in every image.",
  "pages": [
    {{
      "page_number": 1,
      "text": "Story text for this page...",
      "visual_description": "MUST include the complete visual_anchor. Describe setting, action, emotion. Keep outfit IDENTICAL to visual_anchor."
    }},
    // ... continue for all pages ...
  ]
}}

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
                    character_companion: str = "") -> str:
    """Build the complete prompt with all placeholders filled in."""
    
    # Get age-appropriate prompt
    base_prompt = get_prompt_for_age(age)
    
    # Format placeholders
    family_text = f"FAMILY: {family_info}" if family_info else ""
    hero_text = f"HERO TRAIT: {hero_trait}" if hero_trait else ""
    character_text = f"FAMOUS CHARACTER COMPANION: Include {character_companion} as a friend in the story with dialogue." if character_companion else ""
    
    # Fill in placeholders
    prompt = base_prompt.format(
        child_name=child_name,
        age=age,
        gender=gender,
        story_theme=story_theme,
        language=language,
        family_info=family_text,
        hero_trait=hero_text,
        character_companion=character_text
    )
    
    # Add visual consistency rules
    visual_rules = VISUAL_CONSISTENCY_RULES.format(
        child_name=child_name,
        character_companion=character_companion if character_companion else "N/A"
    )
    
    # Add output format
    output = OUTPUT_FORMAT.format(child_name=child_name)
    
    return prompt + "\n\n" + visual_rules + "\n\n" + output


# ============================================================================
# IMAGE STYLE DESCRIPTIONS
# ============================================================================
IMAGE_STYLES = {
    "Cartoon/Animated (3D Pixar Style)": "3D Pixar style animation, vibrant colors, soft lighting, children's book art, high quality, detailed, cute cartoon characters",
    "Cartoon (2D Flat Style)": "2D flat cartoon style, bold outlines, bright colors, simple shapes, children's book illustration, clean vector art style",
    "Photorealistic": "Photorealistic photograph, highly detailed, natural lighting, realistic textures, professional photography, lifelike human figures, real-world setting",
    "Watercolor Illustration": "Watercolor painting style, soft edges, gentle colors, artistic brushstrokes, traditional illustration, dreamy aesthetic",
    "Storybook Classic": "Classic storybook illustration, warm colors, nostalgic feel, traditional children's book art, hand-drawn style, detailed backgrounds"
}

def get_image_style(style_name: str) -> str:
    """Return the image style modifiers for the selected style."""
    return IMAGE_STYLES.get(style_name, IMAGE_STYLES["Cartoon/Animated (3D Pixar Style)"])

