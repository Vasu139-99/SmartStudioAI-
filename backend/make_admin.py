import sys
import os

# Add the current directory to sys.path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import get_connection

def promote_to_admin(email):
    """Promote a user to admin in the database."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if user exists
        cursor.execute("SELECT id, username, is_admin FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            print(f"❌ Error: User with email '{email}' not found.")
            return

        print(f"Found user: {user['username']} (ID: {user['id']})")
        
        if user['is_admin']:
            print(f"ℹ️ User '{email}' is already an admin.")
            return

        # Update is_admin
        cursor.execute("UPDATE users SET is_admin = 1, is_verified = 1 WHERE email = %s", (email,))
        conn.commit()

        print(f"✅ Success: User '{email}' has been promoted to Admin and verified.")

    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)

    email_address = sys.argv[1].strip().lower()
    promote_to_admin(email_address)
