# 🚀 Render Deployment Guide (Web Service)

## ✅ What Changed?

Your bot is now configured to run as a **Web Service** on Render's free tier!

### Changes Made:
1. ✅ Added **Flask web server** wrapper
2. ✅ Changed `Procfile` from `worker:` to `web:`
3. ✅ Added Flask to `requirements.txt`
4. ✅ Bot runs in background thread while Flask handles HTTP requests

---

## 📁 Files You Need to Upload

Upload these **5 files** to your GitHub repo:

1. **bot.py** - Main bot file (modified with Flask)
2. **requirements.txt** - Dependencies (with Flask added)
3. **Procfile** - Tells Render how to run (uses `web:`)
4. **.gitignore** - Ignores unnecessary files
5. **README.md** - Your existing README

---

## 🎯 Deployment Steps

### Step 1: Upload to GitHub

**Option A: GitHub Web Interface**
1. Go to your GitHub repo
2. Click "Add file" → "Upload files"
3. Drag all 5 files
4. Click "Commit changes"

**Option B: Git Command Line**
```bash
git add .
git commit -m "Updated for Render web service"
git push
```

---

### Step 2: Deploy on Render

1. Go to [Render.com](https://render.com)
2. Click "New +" → "**Web Service**"
3. Connect your GitHub repo

**Configure Settings:**

| Setting | Value |
|---------|-------|
| **Name** | `telegram-login-bot` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python bot.py` |
| **Instance Type** | **Free** ⭐ |

4. **Add Environment Variable:**
   - Click "Environment" tab
   - Add variable:
     - **Key**: `BOT_TOKEN`
     - **Value**: Your bot token from BotFather

5. Click "**Create Web Service**"

6. Wait 2-3 minutes for deployment ✅

---

## ✅ How It Works

```
┌─────────────────────────────────────┐
│         Render Web Service          │
│                                     │
│  ┌──────────────────────────────┐  │
│  │    Flask Web Server          │  │
│  │    (Port 5000)               │  │
│  │    - Keeps service alive     │  │
│  │    - Health checks: OK       │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Telegram Bot               │  │
│  │   (Background Thread)        │  │
│  │   - Handles all commands     │  │
│  │   - Processes files          │  │
│  │   - Gets OTP codes           │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## 🧪 Testing

After deployment:

1. **Check Render Logs:**
   - Should see: "🤖 Bot is running..."
   - Should see: "🌐 Starting Flask server..."

2. **Test Bot:**
   - Open Telegram
   - Find your bot
   - Send `/start`
   - Should get welcome message ✅

3. **Check Web Service:**
   - Visit your Render URL (e.g., `https://your-app.onrender.com`)
   - Should see: "🤖 Telegram Bot is Running!"

---

## ⚠️ Important Notes

### Free Tier Limitations:
- ✅ 750 hours/month (plenty for one bot!)
- ⚠️ Service sleeps after **15 minutes** of inactivity
- ✅ Wakes up automatically when someone uses bot (takes ~30 seconds)

### First Message Delay:
If bot was sleeping, first message might take 30-60 seconds. This is normal! Subsequent messages are instant.

### Keep Bot Awake (Optional):
If you want zero delays, upgrade to Render's paid plan ($7/month) or use a service like [Uptime Robot](https://uptimerobot.com) to ping your URL every 5 minutes.

---

## 🐛 Troubleshooting

### Bot Not Responding?
1. Check Render logs for errors
2. Verify `BOT_TOKEN` is correct
3. Make sure service status is "Live"

### "Deploy Failed"?
1. Check all 5 files are uploaded
2. Verify `requirements.txt` has Flask
3. Check logs for specific error

### "Module not found"?
- `requirements.txt` might not have installed
- Check build logs in Render dashboard

---

## 🔄 Updating Your Bot

To update:

```bash
# Make changes to bot.py
git add .
git commit -m "Updated bot features"
git push
```

Render will automatically redeploy! 🚀

---

## 💰 Cost

**100% FREE** on Render!

No credit card required for free tier.

---

## 🎉 You're Done!

Your bot is now live 24/7 on Render!

Test it by sending `/start` to your bot on Telegram.

Happy botting! 🤖✨
