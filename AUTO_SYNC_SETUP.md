# Auto-Sync to GitHub Setup

## Method 1: Credential Storage (One-Time Setup)

This stores your GitHub credentials so you don't need to enter them every time.

### Step 1: Create Personal Access Token
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: "Children Book Generator"
4. Select scope: `repo` (full control)
5. Generate and **copy the token**

### Step 2: Push Once (to store credentials)
```bash
cd "/Users/rahulshah/Desktop/Business/Story book"
git push -u origin main
```
- Username: `rahul311291`
- Password: `paste_your_token_here`

After this, your credentials are stored and you won't need to enter them again!

## Method 2: Easy Sync Script

I've created a `sync_to_github.sh` script for you. Just run:

```bash
# Sync with auto-generated message
./sync_to_github.sh

# Or with custom message
./sync_to_github.sh "Fixed text placement in PDF"
```

## Method 3: Git Alias (Quick Commands)

Add these aliases for super quick syncing:

```bash
# Add to your ~/.zshrc or ~/.bashrc
git config --global alias.sync '!git add . && git commit -m "Auto-sync" && git push'

# Then just run:
git sync
```

## Method 4: Auto-Sync on File Changes (Advanced)

If you want automatic syncing whenever files change, you can use a file watcher. However, **be careful** - this will commit everything automatically, which might not always be desired.

### Using fswatch (if installed):
```bash
# Install fswatch
brew install fswatch

# Watch for changes and auto-sync
fswatch -o . | xargs -n1 -I{} ./sync_to_github.sh "Auto-sync: File changes detected"
```

## Recommended Workflow

**Best Practice**: Use Method 1 (credential storage) + Method 2 (sync script)

1. **One-time setup**: Store credentials (Method 1)
2. **Daily use**: Run `./sync_to_github.sh "Description of changes"` whenever you make changes

## Quick Reference

```bash
# Check status
git status

# Sync to GitHub (easy way)
./sync_to_github.sh "Your commit message"

# Or manually
git add .
git commit -m "Your message"
git push
```

