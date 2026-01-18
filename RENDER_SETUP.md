# Render.com Deployment Setup Guide

This guide explains how to deploy your Children's Book Generator to Render.com and configure the necessary environment variables.

## Prerequisites

1. A [Render.com](https://render.com) account (free tier available)
2. A Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Your Supabase project credentials

## Step 1: Create a New Web Service on Render.com

1. Log in to your [Render.com dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository (or use the manual deployment option)
4. Configure your service:
   - **Name**: Choose a name for your app (e.g., `childrens-book-generator`)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run main.py --server.port=$PORT --server.address=0.0.0.0`

## Step 2: Configure Environment Variables

In your Render.com service settings, go to the "Environment" tab and add the following environment variables:

### Required Environment Variables

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `GEMINI_API_KEY` | Your Gemini API key | Get from https://makersuite.google.com/app/apikey |
| `SUPABASE_URL` | Your Supabase project URL | Format: `https://xxxxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Your Supabase anonymous key | Found in Supabase project settings |

### Optional Environment Variables

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `VITE_SUPABASE_URL` | Same as SUPABASE_URL | For frontend compatibility |
| `VITE_SUPABASE_ANON_KEY` | Same as SUPABASE_ANON_KEY | For frontend compatibility |

## Step 3: Get Your Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the API key (it starts with "AIza...")
5. **IMPORTANT:** Save this key securely - you won't be able to see it again

### API Key Features

- **Free Tier**: Google provides a generous free tier for Gemini API
- **Rate Limits**: Check current limits at https://ai.google.dev/pricing
- **Security**: Never commit your API key to Git. Always use environment variables.

## Step 4: Get Your Supabase Credentials

1. Log in to your [Supabase dashboard](https://app.supabase.com/)
2. Select your project
3. Go to **Settings** → **API**
4. Copy the following:
   - **Project URL** (under "Project URL")
   - **anon/public key** (under "Project API keys")

## Step 5: Add Environment Variables to Render

1. In your Render.com service dashboard, click on "Environment"
2. Click "Add Environment Variable"
3. Add each variable one by one:

```
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SUPABASE_URL=https://xirntbejvbrxydhpjnxh.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

4. Click "Save Changes"

## Step 6: Deploy

1. After adding all environment variables, Render will automatically redeploy your service
2. Wait for the deployment to complete (this may take 5-10 minutes for the first deployment)
3. Once deployed, click on the URL provided by Render to access your app

## Troubleshooting

### Images Not Generating

If you see "API Key Required for Image Generation":

1. **Check Environment Variables**: Make sure `GEMINI_API_KEY` is set in Render.com
2. **Check API Key Length**: The sidebar should show "API key loaded from environment (length: XX chars)"
3. **Check Debug Info**: If the API key is missing, click the debug expander in the error message
4. **Verify API Key**: Test your API key at https://ai.google.dev/tutorials/rest_quickstart

### Common Issues

1. **"API key loaded from environment" shows 0 chars**
   - The environment variable is not set correctly in Render
   - Go to Environment tab and add `GEMINI_API_KEY`

2. **"401 Unauthorized" errors**
   - Your API key is invalid or expired
   - Get a new API key from Google AI Studio

3. **"429 Too Many Requests" errors**
   - You've exceeded your API quota
   - Wait for your quota to reset (usually midnight Pacific Time)
   - Upgrade your Google AI Studio plan for higher limits

4. **App crashes on startup**
   - Check the Render logs for error messages
   - Ensure all required packages are in requirements.txt
   - Verify Python version compatibility

## Security Best Practices

1. **Never commit API keys** to your Git repository
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** regularly
4. **Monitor API usage** in Google AI Studio
5. **Set up alerts** for unusual activity

## Monitoring

1. **Render Logs**: Check the "Logs" tab in your Render dashboard for errors
2. **API Usage**: Monitor your Gemini API usage at https://makersuite.google.com/app/apikey
3. **Supabase Usage**: Check your Supabase dashboard for database usage

## Next Steps

Once deployed, you can:
- Share the Render URL with users
- Set up a custom domain (Render Pro plan)
- Configure auto-scaling (Render Pro plan)
- Set up monitoring and alerts

## Support

If you encounter issues:
- Check Render.com status: https://status.render.com
- Check Google AI status: https://status.cloud.google.com
- Check Supabase status: https://status.supabase.com
- Review logs in Render dashboard

## Cost Considerations

- **Render Free Tier**: Free for hobby projects, with some limitations
- **Google Gemini API**: Generous free tier, pay-as-you-go for higher usage
- **Supabase Free Tier**: Free for small projects, with usage limits

Monitor your usage to avoid unexpected costs.
