import os
from flask import Flask, render_template, session, redirect
from routes.project_routes import project_bp
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from database.db import init_db
from config.settings import settings

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Secret key for sessions
app.secret_key = "smartstudio_ai_secret_key_2026_change_in_production"

# Allow large uploads (100MB)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

# Register blueprints
app.register_blueprint(project_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)


# ─── Page Routes ───

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


# Fix favicon error
@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    # Initialize directories
    settings.init_dirs()

    # Initialize database
    init_db()

    print("\n🚀 SmartStudio AI starting...")
    print("📂 Uploads:", settings.UPLOAD_FOLDER)
    print("📂 Output:", settings.OUTPUT_FOLDER)
    print("🔑 Gemini:", "✅" if settings.GEMINI_API_KEY else "❌")
    print("🔑 DeAPI:", "✅" if settings.DEAPI_KEY else "❌")
    print("🔑 ElevenLabs:", "✅" if settings.ELEVENLABS_API_KEY else "❌")
    print("")

    app.run(debug=True, threaded=True, host="0.0.0.0")