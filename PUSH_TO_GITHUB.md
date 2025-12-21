# How to Push to GitHub

## Step 1: Create a GitHub Repository

1. Go to https://github.com/new
2. Sign in to your GitHub account (or create one if you don't have it)
3. Fill in the repository details:
   - **Repository name**: `children-book-generator` (or any name you prefer)
   - **Description**: "Print-on-Demand Children's Book Generator using Gemini AI"
   - **Visibility**: Choose Public or Private
   - **DO NOT** check "Initialize this repository with a README" (we already have files)
4. Click **"Create repository"**

## Step 2: Copy Your Repository URL

After creating the repo, GitHub will show you a URL like:
- `https://github.com/yourusername/children-book-generator.git`

**Copy this URL** - you'll need it in the next step.

## Step 3: Push Your Code

Open Terminal and run these commands:

```bash
# Navigate to your project
cd "/Users/rahulshah/Desktop/Business/Story book"

# Add the remote repository (replace with YOUR actual URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin main
```

## If You Get Authentication Errors

If you see authentication errors, you have two options:

### Option A: Use GitHub CLI (Recommended)
```bash
# Install GitHub CLI if not installed
brew install gh

# Authenticate
gh auth login

# Then push
git push -u origin main
```

### Option B: Use Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate a new token with `repo` permissions
3. When pushing, use the token as password:
   ```bash
   git push -u origin main
   # Username: your_github_username
   # Password: your_personal_access_token
   ```

## Verify It Worked

After pushing, refresh your GitHub repository page. You should see all your files there!

## Future Updates

Whenever you make changes, use:
```bash
git add .
git commit -m "Description of changes"
git push
```

