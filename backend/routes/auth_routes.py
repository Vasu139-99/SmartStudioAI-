from flask import Blueprint, request, jsonify, session
from database.db import (
    create_user, get_user_by_email, get_user_by_id,
    verify_password, delete_user
)

from functools import wraps

auth_bp = Blueprint("auth_bp", __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm = data.get("confirm_password", "")

    # Validation
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters"}), 400

    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email address"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if not any(c.isupper() for c in password):
        return jsonify({"error": "Password must contain at least one uppercase letter"}), 400
    if not any(c.islower() for c in password):
        return jsonify({"error": "Password must contain at least one lowercase letter"}), 400
    if not any(c.isdigit() for c in password):
        return jsonify({"error": "Password must contain at least one number"}), 400
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>/?`~"
    if not any(c in special_chars for c in password):
        return jsonify({"error": "Password must contain at least one special character"}), 400

    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    # --- Verification Setup (Pending Strategy) ---
    import secrets
    from datetime import datetime, timedelta
    from werkzeug.security import generate_password_hash
    from database.db import create_pending_user, get_user_by_email
    from services.email_service import send_verification_email

    # Check if actually exists
    if get_user_by_email(email):
        return jsonify({"error": "Email already registered"}), 409

    token = secrets.token_hex(16)
    expires_at = datetime.now() + timedelta(hours=24)
    password_hash = generate_password_hash(password)
    
    # Save to pending_users
    success = create_pending_user(username, email, password_hash, token, expires_at)
    if not success:
         return jsonify({"error": "Registration failed, please try again"}), 500

    # Send email
    send_verification_email(email, token)
    # ---------------------------

    return jsonify({
        "message": "Account created! Please check your email to verify and activate your dashboard.",
        "user": {"username": username, "email": email}
    }), 201


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = get_user_by_email(email)

    if not user or not verify_password(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Set session
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["is_admin"] = bool(user.get("is_admin", 0))

    return jsonify({
        "message": "Login successful!",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    })


@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route('/api/me', methods=['GET'])
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = get_user_by_id(user_id)

    if not user:
        session.clear()
        return jsonify({"error": "User not found"}), 401

    return jsonify({
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    })


@auth_bp.route('/api/account', methods=['DELETE'])
def delete_account():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    delete_user(user_id)
    session.clear()

    return jsonify({"message": "Account and all projects deleted successfully"})


# ═══════════════════════════════
# VERIFICATION ROUTE
# ═══════════════════════════════

from flask import render_template

@auth_bp.route('/verify', methods=['GET'])
def verify_page():
    token = request.args.get("token")
    if not token:
        return render_template("verify.html", error="Verification token is missing.")

    from database.db import get_pending_user, create_user_direct, delete_pending_user
    from datetime import datetime

    pending = get_pending_user(token)
    if not pending:
         return render_template("verify.html", error="Invalid or expired verification token.")
         
    # Check if expired
    if "expires_at" in pending and pending["expires_at"] < datetime.now():
         return render_template("verify.html", error="Verification token has expired.")
    
    # Move to main users table
    user_id = create_user_direct(pending["username"], pending["email"], pending["password_hash"])
    if not user_id:
         return render_template("verify.html", error="Activation failed. Email might have been registered recently.")

    # Clean up
    delete_pending_user(token)
    
    return render_template("verify.html", success=True)
