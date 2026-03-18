# 🎬 SmartStudio AI

SmartStudio AI is an **AI-powered automated video generation platform** that transforms static images and scripts into high-quality, fully voiced cinematic videos with dynamic translated captions.

---

## 🚀 Features

*   **User Authentication**: Secure Login & Registration using session profiles and remote database integration.
*   **AI Script Generator**: Uses **Google Gemini** to analyze uploaded images and generate engaging story narratives.
*   **Image-to-Video Animation**: Integrates **DeAPI** to create cinematic 3D effects from static files.
*   **Voice Narration Output**: Integrates **ElevenLabs** for human-like narration voice-overs for video timelines.
*   **Auto Captions Translation**: Translates and synchronizes hardcoded VTT subtitles over generated videos using Whisper frameworks.
*   **Multi-Aspect Ratio Styles**: Supports vertical (`9:16`) and horizontal (`16:9`) render queues.

---

## 🛠️ Technology Stack

*   **Backend Framework**: [Flask](https://flask.palletsprojects.com/) (Python 3.11+)
*   **Database Engine**: [TiDB Cloud](https://pingcap.com/tidb-cloud) (MySQL Compatible with strict TLS)
*   **Core AI Pipelines**: Gemini AI, ElevenLabs, DeAPI Endpoint node
*   **Media Editing core**: MoviePy + FFMPEG
*   **Subtitles system**: OpenAI-Whisper + Pysrt

---

## 💻 Local Setup Instructions

### 📝 1. Prerequisites
Make sure you have **Python 3.10** or **3.11** installed on your system.

### ⚙️ 2. Installation
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Vasu139-99/SmartStudioAI-.git
    cd SmartStudioAI-
    ```

2.  **Initialize Virtual Environment**:
    ```bash
    python -m venv backend/venv
    ```

3.  **Activate Virtual Environment**:
    *   **Windows**: `backend\venv\Scripts\activate`
    *   **Mac/Linux**: `source backend/venv/bin/activate`

4.  **Install Dependencies**:
    ```bash
    pip install -r backend/requirements.txt
    ```

---

## 🔑 3. Environment Variables (`.env`)

Create a `.env` file in the **Root Directory** of your project (same level as the `.git` folder) and populate the following keys:

```env
# AI APIs
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_eleven_labs_key
DEAPI_KEY=your_deapi_rotating_keys_separated_by_commas

# Narration Profile
VOICE_ID=your_elevenlabs_voice_id_here

# Database Configuration
MYSQL_HOST=your_tidb_host
MYSQL_USER=your_tidb_username
MYSQL_PASSWORD=your_tidb_password
MYSQL_DB=test
MYSQL_PORT=4000
MYSQL_SSL=true

# Mail fallback configuration
EMAIL_USER=your_gmail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
```

---

## 🏃 Running the Application

1.  Navigate into the backend setup (if not inside venv node):
2.  Start the development server:
    ```bash
    python backend/app.py
    ```
3.  Open [http://localhost:5000](http://localhost:5000) in your web browser.

---

## ☁️ Cloud Deployment (Render.com)

*   **Environment type**: Python 3
*   **Python Version Variable**: `PYTHON_VERSION=3.11.11`
*   **Root Directory**: Leave it to default (None / Empty) or set to `backend`
*   **Build Command**: `pip install -r backend/requirements.txt`
*   **Start Command**: `gunicorn backend.app:app`
