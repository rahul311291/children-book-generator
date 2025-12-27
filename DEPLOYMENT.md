# Deployment Guide

This is a **Python/Streamlit application**, not a Node.js app.

## Deployment Configuration Files

The following files have been added for deployment:

### For All Platforms
- **`requirements.txt`** - Python dependencies
- **`.env`** - Environment variables (Supabase credentials)
- **`Procfile`** - Process configuration for web dyno
- **`runtime.txt`** - Python version specification

### For Streamlit-Specific Platforms
- **`.streamlit/config.toml`** - Streamlit configuration
- **`streamlit_app.py`** - Alternative entry point
- **`setup.sh`** - Setup script for Streamlit Cloud

### For Mixed Platforms
- **`package.json`** - Minimal Node config to prevent npm errors

## Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repository
3. Select `main.py` as the main file
4. Add environment variables from `.env`:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `GEMINI_API_KEY` (optional)
5. Deploy

**Entry Point**: `main.py`

### Option 2: Heroku
```bash
heroku create your-app-name
heroku config:set VITE_SUPABASE_URL=https://xirntbejvbrxydhpjnxh.supabase.co
heroku config:set VITE_SUPABASE_ANON_KEY=your_key_here
git push heroku main
```

**Entry Point**: Uses `Procfile` to run `streamlit run main.py`

### Option 3: Railway
1. Connect GitHub repository
2. Railway auto-detects Python from `requirements.txt`
3. Add environment variables
4. Deploy

**Entry Point**: Uses `Procfile` or `main.py`

### Option 4: Render
1. Create new Web Service
2. Connect repository
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `streamlit run main.py --server.port=$PORT --server.address=0.0.0.0`
5. Add environment variables
6. Deploy

### Option 5: Docker (Any Platform)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Environment Variables Required

All deployment platforms need these environment variables:

```env
VITE_SUPABASE_URL=https://xirntbejvbrxydhpjnxh.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
```

Optional:
```env
GEMINI_API_KEY=your_gemini_api_key
```

## Entry Points

The app can be started from multiple entry points:
- **`main.py`** - Primary entry point (recommended)
- **`streamlit_app.py`** - Alternative for Streamlit Cloud
- **`app.py`** - Alternative for generic platforms

All three run the same application.

## Port Configuration

The app automatically detects the port:
- Uses `$PORT` environment variable if available
- Falls back to default Streamlit port (8501)

## Database

The app uses **Supabase** (cloud PostgreSQL):
- No database setup needed on deployment platform
- Credentials in environment variables connect to cloud database
- Database is already populated with template data
- Works identically across all deployment platforms

## Build Process

**No build process needed** - this is a Python app:
1. Platform installs dependencies from `requirements.txt`
2. Platform runs `streamlit run main.py`
3. App connects to Supabase database
4. Ready to use!

## Troubleshooting

### "Cannot find package.json"
- **Fixed**: Added minimal `package.json` to satisfy npm-based platforms
- The `package.json` just points to Python install/run commands

### "Module not found"
- Check all dependencies in `requirements.txt` are installed
- Run: `pip install -r requirements.txt`

### "Database connection failed"
- Verify environment variables are set correctly
- Check Supabase URL and key are valid
- Test connection: `python seed_template_data.py`

### "Port already in use"
- Streamlit defaults to port 8501
- Deployment platforms override with `$PORT` variable
- Manual: `streamlit run main.py --server.port=8080`

## Local Testing Before Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Test database connection
python seed_template_data.py

# Run app locally
streamlit run main.py

# Or with custom port
streamlit run main.py --server.port=8080
```

## Post-Deployment Checklist

- [ ] App loads without errors
- [ ] "Template Book" mode is available
- [ ] Database loads 24 profession pages
- [ ] Can create personalized book preview
- [ ] Photos can be uploaded
- [ ] Environment variables are set
- [ ] Logs show no errors

## Support

If deployment fails:
1. Check platform logs for specific error
2. Verify all environment variables are set
3. Ensure `requirements.txt` dependencies install correctly
4. Test database connection manually
5. Contact platform support if needed

---

**Remember**: This is a Python/Streamlit application. The `package.json` file is only included to prevent npm errors on mixed platforms. The actual runtime is Python 3.11+.
