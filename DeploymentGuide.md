# SmartStudio AI - Deployment Guide

This guide will walk you through deploying your SmartStudio AI project to **GitHub** and then hosting it on **Render**.

---

## 🛠️ Step 1: Workspace Prep
I have already prepared your workspace with the following **optimizations**:
1.  **Deleted Unnecessary Files**: Test scripts (`test_*.py`), debug files (`get_token_vasu.py`), and temporary uploads to keep your repository clean.
2.  **Created `.gitignore`**: This is critical! It prevents sensitive files like `.env` (your API keys) and local virtual environments (`venv`) from being uploaded to GitHub.
3.  **Updated `requirements.txt`**: Added `gunicorn` which is a production-ready WSGI server required by Render.

---

## 📤 Step 2: Push to GitHub

To push your code to GitHub, open your terminal (e.g., PowerShell) in the `d:\SmartStudioAI` folder and run these commands:

1.  **Initialize Git & Commit** (I have already run `git init` for you!):
    If you haven't committed yet, you can run:
    ```powershell
    git add .
    git commit -m "Initial commit - Ready for Render"
    ```
    *(The `.gitignore` will automatically exclude `.env` and `venv`)*

2.  **Create a New Repository on GitHub**:
    -   Go to [github.com/new](https://github.com/new)
    -   Give it a name (e.g., `SmartStudioAI`)
    -   Do **not** initialize with README, `.gitignore`, or License (we already have them).

3.  **Link and Push**:
    Find the Git URL of your new GitHub repo and run:
    ```powershell
    git remote add origin https://github.com/YOUR_USERNAME/SmartStudioAI.git
    git push -u origin main
    ```
    *(Replace `YOUR_USERNAME` with your actual GitHub username)*

---

## 🚀 Step 3: Deploy to Render

Render is excellent for hosting Flask apps. Follow these steps:

1.  **Log in to Render**:
    -   Go to [dashboard.render.com](https://dashboard.render.com) and sign in (you can use your GitHub account).

2.  **Create a New Web Service**:
    -   Click **New** -> **Web Service**.
    -   Select **Build and deploy from a Git repository** and pick your `SmartStudioAI` repo.

3.  **Configure Web Service**:
    -   **Name**: `smartstudio-ai` (or any URL name you like)
    -   **Runtime**: `Python`
    -   **Branch**: `main`
    -   **Root Directory**: **`backend`**  *(💡 This is required so Render runs from the right folder!)*
    -   **Build Command**: **`pip install -r requirements.txt`**
    -   **Start Command**: **`gunicorn app:app`**

4.  **Add Environment Variables (CRITICAL)**:
    -   Scroll down to **Advanced** -> **Environment Variables**.
    -   Add all the keys from your local `.env` file here. For example:
        *   `GEMINI_API_KEY` = `your_actual_api_key`
        *   `DEAPI_KEY` = `...`
        *   `ELEVENLABS_API_KEY` = `...`
    -   *Do NOT upload the `.env` file. Transfer the variables row by row in the Render dashboard.*

5.  **Deploy**:
    -   Click **Create Web Service**.
    -   Render will build your app and deploy it!

---

## ⚠️ Common Errors & Fixes

### 🔴 Error: `ModuleNotFoundError: No module named 'pyaudioop'`
This happens because Render tries to use **Python 3.13+**, which removed a core audio module that `pydub` needs.

**✅ The Fix**:
1.  Go to your Render Web Service **Settings**.
2.  Scroll to **Environment Variables** (or click the tab).
3.  Click **Add Environment Variable**:
    *   **Key**: `PYTHON_VERSION`
    *   **Value**: `3.11.8`
4.  Save and click **Manual Deploy ➜ Clear Build Cache & Deploy**.

---

### 🔴 Error: `Network error. Please try again.` on Registration
This happens when the **Database Connection fails** on the Render server. 

**✅ The Cause**:
Your `.env` file likely has `MYSQL_HOST=localhost`. 
Render containers run in isolated environments and **cannot connect to `localhost` for MySQL** (unless running a local file like SQLite). You must use a **Hosted MySQL Database** (e.g., Clever Cloud, PlanetScale, or Render Managed DB) and provide its full remote hostname.

**✅ The Fix**:
1. Get a hosted MySQL instance and its Connection String.
2. Go to your Render Web Service **Settings** -> **Environment Variables**.
3. Update `MYSQL_HOST` to your **Hosted Database Domain/IP** (not `localhost`).
4. Update `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DB` to match.

---

### 💡 Pro-Tip
If you make code changes in the future, just run:
```powershell
git add .
git commit -m "your update message"
git push
```
Render will **automatically** redeploy your app upon pushing to GitHub!
