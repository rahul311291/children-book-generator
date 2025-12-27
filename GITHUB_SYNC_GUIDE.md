# GitHub Sync Guide

## Your Repository
Your code is at: https://github.com/rahul311291/children-book-generator

## How to Push Changes to GitHub

### 1. Quick Push (One Command)
```bash
cd "/Users/rahulshah/Desktop/Business/Story book"
git add . && git commit -m "Your message here" && git push
```

### 2. Step-by-Step Push
```bash
# Navigate to your project
cd "/Users/rahulshah/Desktop/Business/Story book"

# See what changed
git status

# Add all changes
git add .

# Commit with a message
git commit -m "Describe your changes"

# Push to GitHub
git push
```

---

## How to Pull to Another Computer/App

### First Time Setup (New Computer)
```bash
# Clone the repository
git clone https://github.com/rahul311291/children-book-generator.git

# Navigate into the folder
cd children-book-generator

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run main.py
```

### Already Cloned? Just Pull Updates
```bash
cd children-book-generator
git pull
```

---

## Using with Cursor on Another Computer

1. **Install Cursor** from https://cursor.sh
2. **Open Cursor**
3. **File → Open Folder** → Select your cloned `children-book-generator` folder
4. **Or clone directly in Cursor:**
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows)
   - Type "Git: Clone"
   - Enter: `https://github.com/rahul311291/children-book-generator.git`

---

## Automatic Sync (Optional)

### Option 1: Git Alias for Quick Sync
Add to your `~/.zshrc` or `~/.bashrc`:
```bash
alias syncbook='cd "/Users/rahulshah/Desktop/Business/Story book" && git add . && git commit -m "Auto sync $(date)" && git push'
```
Then just type `syncbook` to push everything.

### Option 2: Create a Sync Script
Already created: `sync_to_github.sh`
```bash
./sync_to_github.sh
```

---

## Editing Prompts

### Where to Edit
All prompts are in one file: **`story_prompts.py`**

### What You Can Edit
1. **Age-specific prompts**: `AGE_2_3_PROMPT`, `AGE_3_4_PROMPT`, etc.
2. **Image styles**: `IMAGE_STYLES` dictionary
3. **Visual consistency rules**: `VISUAL_CONSISTENCY_RULES`
4. **Output format**: `OUTPUT_FORMAT`

### How to Edit
1. Open `story_prompts.py` in any text editor
2. Find the age group you want to modify (search for `AGE_4_5_PROMPT` etc.)
3. Edit the text between the triple quotes
4. Save the file
5. Restart the Streamlit app

### Placeholders You Can Use
- `{child_name}` - The child's name
- `{age}` - The child's age
- `{gender}` - The child's gender
- `{story_theme}` - The story theme/problem
- `{language}` - English or Hindi
- `{family_info}` - Family structure
- `{hero_trait}` - Child's strength
- `{character_companion}` - Famous character (if any)

---

## Troubleshooting

### "Permission denied" when pushing
```bash
git config --global credential.helper osxkeychain
git push  # Enter your GitHub username and personal access token
```

### "Merge conflict"
```bash
git pull
# Edit conflicting files
git add .
git commit -m "Resolved conflicts"
git push
```

### "Authentication failed"
You need a Personal Access Token (not password):
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`
4. Use this token as your password

---

## File Structure

```
children-book-generator/
├── main.py                 # Main application (don't edit prompts here)
├── story_prompts.py        # ← EDIT THIS FILE for prompts
├── requirements.txt        # Python dependencies
├── API_KEY_SETUP.md        # API key setup guide
├── GITHUB_SYNC_GUIDE.md    # This file
├── saved_stories/          # Saved stories (not synced)
└── logs/                   # Log files (not synced)
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Push changes | `git add . && git commit -m "message" && git push` |
| Pull updates | `git pull` |
| Check status | `git status` |
| View history | `git log --oneline` |
| Clone on new PC | `git clone https://github.com/rahul311291/children-book-generator.git` |

