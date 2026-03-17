import pymysql
import certifi
import os
import json
import shutil
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config.settings import settings
from pymysql.cursors import DictCursor


def get_connection():
    ssl_config = {'ca': certifi.where()} if settings.MYSQL_SSL else None
    
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        port=settings.MYSQL_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True,
        ssl=ssl_config
    )


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        is_verified BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_users (
        token VARCHAR(100) PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        expires_at TIMESTAMP NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id VARCHAR(40) PRIMARY KEY,
        user_id INT,
        product_name VARCHAR(255),
        image_paths TEXT,
        script TEXT,
        language VARCHAR(100) DEFAULT 'English',
        aspect_ratio VARCHAR(20) DEFAULT '9:16',
        scene_prompts TEXT,
        voice_path TEXT,
        video_path TEXT,
        download_path TEXT,
        vtt_paths TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        current_step VARCHAR(255) DEFAULT '',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Verification tokens table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_tokens (
        user_id INT,
        token VARCHAR(100) PRIMARY KEY,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Password resets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        email VARCHAR(255) PRIMARY KEY,
        otp VARCHAR(6) NOT NULL,
        expires_at TIMESTAMP NOT NULL
    )
    """)

    # Add is_admin column if upgrading from old schema
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
    except pymysql.err.OperationalError as e:
        if e.args[0] != 1060:  # 1060 = Duplicate Column
            raise

    # Add is_verified column if upgrading
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE")
    except pymysql.err.OperationalError as e:
        if e.args[0] != 1060:
            raise

    cursor.close()
    conn.close()


# ═══════════════════════════════
# USER CRUD
# ═══════════════════════════════

def create_user(username, email, password):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return user_id
    except pymysql.err.IntegrityError:
        cursor.close()
        conn.close()
        return None  # Email already exists


def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, created_at, is_admin FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)


def delete_user(user_id):
    """Delete user and all their projects + files"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get all project IDs for cleanup
    cursor.execute("SELECT id FROM projects WHERE user_id = %s", (user_id,))
    project_ids = [row["id"] for row in cursor.fetchall()]

    # Delete projects from DB (cascade)
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # Cleanup files for each project
    for pid in project_ids:
        _cleanup_project_files(pid)

    return True


# ═══════════════════════════════
# EMAIL VERIFICATION HELPERS
# ═══════════════════════════════

def create_verification_token(user_id, token, expires_at):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO verification_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at)
        )
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating token: {e}")
        cursor.close()
        conn.close()
        return False

def get_verification_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verification_tokens WHERE token = %s", (token,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None

def verify_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    # 1. Update user
    cursor.execute("UPDATE users SET is_verified = 1 WHERE id = %s", (user_id,))
    # 2. Delete token
    cursor.execute("DELETE FROM verification_tokens WHERE user_id = %s", (user_id,))
    cursor.close()
    conn.close()
    return True


# ═══════════════════════════════
# PENDING USER HELPERS
# ═══════════════════════════════

def create_pending_user(username, email, password_hash, token, expires_at):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO pending_users (username, email, password_hash, token, expires_at) VALUES (%s, %s, %s, %s, %s)",
            (username, email, password_hash, token, expires_at)
        )
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating pending user: {e}")
        cursor.close()
        conn.close()
        return False

def get_pending_user(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_users WHERE token = %s", (token,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None

def delete_pending_user(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_users WHERE token = %s", (token,))
    cursor.close()
    conn.close()
    return True

def get_all_pending_users():
    """Retrieve all pending users for Admin view Node."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, expires_at FROM pending_users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def create_user_direct(username, email, password_hash):
    """Create user skipping raw-hash workflows and set verified immediately Node."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_verified) VALUES (%s, %s, %s, 1)",
            (username, email, password_hash)
        )
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return user_id
    except Exception as e:
        print(f"Error direct insert user: {e}")
        cursor.close()
        conn.close()
        return None


# ═══════════════════════════════
# PASSWORD RESET HELPERS
# ═══════════════════════════════

def create_password_reset(email, otp, expires_at):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "REPLACE INTO password_resets (email, otp, expires_at) VALUES (%s, %s, %s)",
            (email, otp, expires_at)
        )
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating reset: {e}")
        cursor.close()
        conn.close()
        return False

def get_password_reset(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM password_resets WHERE email = %s", (email,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None

def delete_password_reset(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM password_resets WHERE email = %s", (email,))
    cursor.close()
    conn.close()
    return True

def update_password(email, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating password: {e}")
        cursor.close()
        conn.close()
        return False


# ═══════════════════════════════
# PROJECT CRUD
# ═══════════════════════════════

def create_project(project_id, product_name, image_paths, user_id=None, language='English', aspect_ratio='9:16'):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO projects (id, user_id, product_name, image_paths, language, aspect_ratio, status, current_step)
    VALUES (%s, %s, %s, %s, %s, %s, 'processing', 'Uploading images')
    """, (project_id, user_id, product_name, json.dumps(image_paths), language, aspect_ratio))

    conn.commit()
    cursor.close()
    conn.close()


def update_project(project_id, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()

    fields = []
    values = []
    for key, val in kwargs.items():
        fields.append(f"{key} = %s")
        values.append(val)

    values.append(project_id)

    cursor.execute(
        f"UPDATE projects SET {', '.join(fields)} WHERE id = %s",
        values
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_project(project_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return dict(row)
    return None


def get_all_projects(user_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute(
            "SELECT * FROM projects WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        )
    else:
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT 20")

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [dict(row) for row in rows]


def delete_project(project_id):
    """Delete a project from DB and remove its files"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()

    _cleanup_project_files(project_id)
    return True


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, is_admin, created_at FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def _cleanup_project_files(project_id):
    """Remove upload, temp, and output files for a project"""
    from config.settings import settings

    dirs_to_clean = [
        os.path.join(settings.UPLOAD_FOLDER, project_id),
        os.path.join(settings.TEMP_FOLDER, project_id),
    ]

    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

    # Remove output video
    output_file = os.path.join(settings.OUTPUT_FOLDER, f"{project_id}.mp4")
    if os.path.exists(output_file):
        os.remove(output_file)