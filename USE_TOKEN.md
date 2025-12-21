# How to Use Your GitHub Token

## Method 1: Enter Token When Prompted (Recommended)

When you run `git push`, Git will ask for credentials. Here's what to enter:

```bash
cd "/Users/rahulshah/Desktop/Business/Story book"
git push -u origin main
```

**When prompted:**
- **Username**: `rahul311291`
- **Password**: `paste_your_token_here` (NOT your GitHub password!)

After entering the token once, macOS Keychain will save it and you won't need to enter it again.

## Method 2: Add Token to URL (Temporary)

If Method 1 doesn't work, you can temporarily add the token to the URL:

```bash
# Replace YOUR_TOKEN with your actual token
git remote set-url origin https://rahul311291:YOUR_TOKEN@github.com/rahul311291/children-book-generator.git

# Then push
git push -u origin main

# After successful push, remove token from URL for security
git remote set-url origin https://github.com/rahul311291/children-book-generator.git
```

## Method 3: Use GitHub CLI (Alternative)

```bash
# Install GitHub CLI
brew install gh

# Login (will open browser)
gh auth login

# Then push normally
git push -u origin main
```

## Quick Steps

1. Open Terminal
2. Run: `cd "/Users/rahulshah/Desktop/Business/Story book"`
3. Run: `git push -u origin main`
4. When asked for username: Enter `rahul311291`
5. When asked for password: Paste your token (not your GitHub password!)
6. Done! Your credentials are now saved.

