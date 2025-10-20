# Streamlit Cloud Deployment Troubleshooting

## Error: "You do not have access to this app or it does not exist"

This error occurs when Streamlit Cloud can't access your GitHub repository. Here's how to fix it:

## Solution Steps

### Step 1: Check Repository Visibility

Your repository must be **public** or Streamlit Cloud must have access to your private repositories.

```bash
# Check if repo is public
git remote -v
# Note the GitHub URL
```

Then go to: `https://github.com/your-username/your-repo-name/settings`

- Scroll to **Danger Zone**
- Check if it says "Change repository visibility"
- If it's private, either:
  1. **Make it public** (Recommended for open source)
  2. **Grant Streamlit access** to private repos (see Step 2)

### Step 2: Grant Streamlit Cloud Access to GitHub

1. Go to: https://share.streamlit.io/
2. Click your profile icon (top right)
3. Click **Settings**
4. Under **GitHub**, click **Connect GitHub account**
5. Make sure you're connected with: `github.com/benchay1999`
6. Click **Authorize streamlit** when prompted
7. If asked about organization access, grant it

### Step 3: Re-deploy the App

1. Go back to https://share.streamlit.io/
2. Click **"New app"**
3. **Repository**: Select your repository from the dropdown
   - If you don't see it, click "Refresh" or re-connect GitHub
4. **Branch**: `main` (or your default branch)
5. **Main file path**: `streamlit_cloud_app.py`
6. Click **"Advanced settings"**
7. Add to **Secrets**:
   ```toml
   BACKEND_URL = "https://your-tunnel-url"
   ```
8. Click **"Deploy"**

## Alternative: Deploy from Repository URL

If the dropdown doesn't show your repo:

1. Make sure your repository is public
2. Get your repo URL: `https://github.com/benchay1999/ai-group-chat-streamlit`
3. On Streamlit Cloud, paste the full repository URL instead of selecting from dropdown
4. Set main file path: `streamlit_cloud_app.py`
5. Deploy

## Common Issues

### Issue 1: Wrong GitHub Account

**Symptom**: You're signed in with the wrong GitHub account

**Solution**:
1. Sign out of Streamlit Cloud
2. Sign out of GitHub
3. Clear browser cookies
4. Sign back in to both with `github.com/benchay1999`
5. Try deploying again

### Issue 2: Repository Not Found

**Symptom**: Streamlit can't find your repository

**Solution**:
1. Verify your code is pushed to GitHub:
   ```bash
   git status
   git add .
   git commit -m "Add streamlit cloud deployment"
   git push origin main
   ```
2. Check GitHub web interface to confirm files are there
3. Make sure `streamlit_cloud_app.py` exists in the root directory

### Issue 3: Organization Repository

**Symptom**: Repository is under an organization, not your personal account

**Solution**:
1. Go to: https://github.com/settings/connections/applications/
2. Find **Streamlit**
3. Under "Organization access", grant access to your organization
4. Refresh Streamlit Cloud and try again

## Verify Your Setup

Before deploying, make sure:

```bash
# 1. You're in the right directory
pwd
# Should show: /home/wschay/ai-group-chat-streamlit

# 2. streamlit_cloud_app.py exists
ls -la streamlit_cloud_app.py

# 3. Code is committed and pushed
git status
git log -1

# 4. Check remote URL
git remote get-url origin
```

## Quick Deploy Checklist

- [ ] Repository is public OR Streamlit has access to private repos
- [ ] GitHub account `benchay1999` is connected to Streamlit Cloud
- [ ] Code is pushed to GitHub (`git push origin main`)
- [ ] `streamlit_cloud_app.py` exists in repository root
- [ ] Backend is running locally (`./start_local.sh`)
- [ ] Tunnel is running (ngrok, localhost.run, etc.)
- [ ] You have the tunnel's HTTPS URL ready

## Test Locally First

Before deploying to Streamlit Cloud, test locally:

```bash
# Terminal 1: Backend
./start_local.sh

# Terminal 2: Frontend
export BACKEND_URL=http://localhost:8000
streamlit run streamlit_cloud_app.py
```

If it works locally, the issue is with Streamlit Cloud access, not your code.

## Still Having Issues?

### Check Streamlit Cloud Logs

Once deployed (even if failing):
1. Go to your app on Streamlit Cloud
2. Click **"Manage app"** (bottom right)
3. Click **"Logs"** to see error messages

### Manual Deployment Alternative

If Streamlit Cloud isn't working, you can deploy the frontend elsewhere:

1. **Heroku** (Free tier available)
2. **Render** (Free tier available)
3. **Railway** (Free trial)
4. **Local Streamlit** (Access via tunnel)

See [DEPLOYMENT.md](DEPLOYMENT.md) for alternatives.

## Contact Information

If none of this works:
- Check Streamlit Community: https://discuss.streamlit.io/
- Streamlit Cloud status: https://status.streamlit.io/
- Your email with Streamlit: benchay@kaist.ac.kr

## Quick Fix: Make Repository Public

The fastest solution:

1. Go to: https://github.com/benchay1999/ai-group-chat-streamlit/settings
2. Scroll to **"Danger Zone"**
3. Click **"Change repository visibility"**
4. Select **"Make public"**
5. Confirm
6. Go back to Streamlit Cloud and deploy

This usually solves the access issue immediately! 🎉

