#!/bin/bash

# Simple script to sync changes to GitHub
# Usage: ./sync_to_github.sh "Your commit message"

cd "$(dirname "$0")"

# Check if there are changes
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ No changes to commit"
    exit 0
fi

# Commit message
COMMIT_MSG="${1:-Auto-sync: Updated files}"

echo "📝 Staging changes..."
git add .

echo "💾 Committing changes: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "🚀 Pushing to GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Successfully synced to GitHub!"
else
    echo "❌ Failed to push. Check your authentication."
    exit 1
fi

