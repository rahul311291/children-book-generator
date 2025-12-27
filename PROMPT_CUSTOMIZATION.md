# Prompt Customization Guide

This guide explains the **3 different types of prompts** in the app and where to edit each one.

---

## 📖 1. STORY CREATION PROMPT
**What it does:** Controls how the AI writes the story text for each page

**Location:** `main.py` → Function: `generate_story_with_gemini()` → Lines ~103-131

### What to Edit:

#### A. System Instruction (Lines ~103-126)
This tells the AI **HOW** to write the story:
- Story structure (Problem → Struggle → Solution)
- Writing style (simple, rhythmic, age-appropriate)
- Number of pages
- Language
- Format requirements (JSON structure)

**Example - Change story style:**
```python
# Current: General story
system_instruction = f"""You are an expert children's book author. Write a 10-page story...

# Change to: Rhyming story
system_instruction = f"""You are an expert children's book author. Write a 10-page RHYMING story with catchy verses...
```

#### B. Main Prompt (Lines ~128-131)
This is the **actual request** sent to the AI with child's details:
- Child's name, age, gender
- Problem/theme
- Physical description

**Example - Add more context:**
```python
# Current
prompt = f"""Write a personalized children's story for {child_name}...

# Enhanced
prompt = f"""Write a magical, adventurous children's story for {child_name}...
```

---

## 🎨 2. IMAGE CREATION PROMPT
**What it does:** Controls the **visual style** of all generated images

**Location:** `main.py` → Function: `generate_image_with_imagen()` → Line ~230

### What to Edit:

**Style Modifiers (Line ~230)**
This adds style description to every image prompt:
- Art style (Pixar, watercolor, minimalist, etc.)
- Color scheme
- Lighting
- Overall aesthetic

**Current:**
```python
style_modifiers = "Storybook illustration, vibrant colors, soft lighting, 3D Pixar style, children's book art, high quality, detailed"
```

**Examples:**

```python
# Watercolor style
style_modifiers = "Watercolor painting, soft pastel colors, dreamy atmosphere, children's book illustration, artistic"

# Minimalist style
style_modifiers = "Minimalist illustration, clean lines, simple shapes, modern children's book art, bold colors"

# Realistic style
style_modifiers = "Realistic illustration, detailed artwork, natural lighting, professional children's book quality, lifelike"

# Cartoon style
style_modifiers = "Cartoon illustration, bright colors, playful style, animated children's book art, fun and cheerful"
```

**Note:** This style is added to EVERY image. Individual image prompts can be edited in the UI when regenerating.

---

## 👤 3. CHARACTER DESCRIPTION (Visual Anchor)
**What it does:** Creates a consistent description of the main character that appears in EVERY image

**Location:** `main.py` → Function: `create_visual_anchor()` → Line ~62

### What to Edit:

**Character Template (Line ~62)**
This describes how the character looks consistently across all images:
- Age, gender
- Physical features (from user input)
- Overall appearance

**Current:**
```python
anchor = f"A cute {age} year old {gender.lower()}, {physical_desc.lower()}"
```

**Examples:**

```python
# More detailed character
anchor = f"A charming {age} year old {gender.lower()} with {physical_desc.lower()}, always smiling, bright eyes"

# Different tone
anchor = f"An adorable {age} year old {gender.lower()}, {physical_desc.lower()}, with expressive eyes and a warm smile"

# Add personality
anchor = f"A cheerful {age} year old {gender.lower()}, {physical_desc.lower()}, full of energy and curiosity"
```

**Important:** This description is automatically added to the beginning of every image prompt to keep the character looking the same!

---

## 🎯 Quick Reference

| Prompt Type | What It Controls | Location | Line Number |
|------------|------------------|----------|------------|
| **Story Creation** | How AI writes story text | `generate_story_with_gemini()` | ~103-131 |
| **Image Style** | Visual appearance of images | `generate_image_with_imagen()` | ~230 |
| **Character** | Consistent character appearance | `create_visual_anchor()` | ~62 |

---

## 📝 How to Edit

1. **Open** `main.py` in your code editor
2. **Find** the function/line mentioned above
3. **Edit** the prompt text
4. **Save** the file
5. **Restart** Streamlit: Stop app (Ctrl+C) and run `streamlit run main.py` again
6. **Generate** a new story to see changes

---

## 💡 Tips

- **Story Prompt**: Change this to make stories funnier, more educational, longer/shorter, etc.
- **Image Style**: Change this to get different art styles (watercolor, cartoon, realistic, etc.)
- **Character**: Change this to add more personality or details to the character description

---

## 🔍 Finding the Code

In `main.py`, look for these comments:
- `# ============================================================================`
- `# PROMPT CUSTOMIZATION AREA`
- `# ============================================================================`

These mark the exact sections you can edit!
