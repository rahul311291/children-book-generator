# Secure API Key Setup Guide

## Option 1: Environment Variable (Recommended for Production)

Set the `GEMINI_API_KEY` environment variable on your system. This keeps the key secure and out of your code.

### macOS/Linux:
```bash
# Add to your ~/.zshrc or ~/.bashrc file:
export GEMINI_API_KEY="your-api-key-here"

# Then reload your shell:
source ~/.zshrc  # or source ~/.bashrc
```

### Windows:
```powershell
# In PowerShell:
$env:GEMINI_API_KEY="your-api-key-here"

# Or set it permanently:
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your-api-key-here', 'User')
```

### For Streamlit Cloud/Deployment:
1. Go to your Streamlit Cloud dashboard
2. Click on your app
3. Go to "Settings" → "Secrets"
4. Add:
```
GEMINI_API_KEY=your-api-key-here
```

## Option 2: Manual Entry (Current Method)

You can still enter the API key manually in the sidebar. If an environment variable is set, you'll see a message and can override it if needed.

## Security Notes:
- Never commit your API key to Git
- Use environment variables for production/franchise deployments
- The `.gitignore` file already excludes files that might contain keys

