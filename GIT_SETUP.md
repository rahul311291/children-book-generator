# Git Setup Guide

## Initial Setup

Run these commands in your terminal:

```bash
cd "/Users/rahulshah/Desktop/Business/Story book"

# Initialize Git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Children's Book Generator app"

# (Optional) Add remote repository
# If you have a GitHub/GitLab repository, add it:
# git remote add origin https://github.com/yourusername/your-repo-name.git
# git push -u origin main
```

## Daily Workflow

```bash
# Check status
git status

# Add changes
git add .

# Commit changes
git commit -m "Description of your changes"

# Push to remote (if you have one)
git push
```

## Create a GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (name it something like "children-book-generator")
3. Don't initialize with README (we already have files)
4. Copy the repository URL
5. Run:
   ```bash
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git branch -M main
   git push -u origin main
   ```

## Important Notes

- Never commit API keys or secrets (they're in .gitignore)
- Always review `git status` before committing
- Write clear commit messages describing your changes

