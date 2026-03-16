from flask import Blueprint, render_template, jsonify, session
from routes.auth_routes import admin_required
from database.db import get_all_users, get_all_projects, delete_user, get_all_pending_users

admin_bp = Blueprint("admin_bp", __name__)


@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    return render_template("admin.html")


@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_stats():
    users = get_all_users()
    projects = get_all_projects()
    pending = get_all_pending_users()
    return jsonify({
        "total_users": len(users),
        "total_projects": len(projects),
        "total_pending": len(pending)
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users():
    users = get_all_users()
    return jsonify({"users": users})

@admin_bp.route('/api/admin/pending', methods=['GET'])
@admin_required
def list_pending():
    pending = get_all_pending_users()
    return jsonify({"pending": pending})


@admin_bp.route('/api/admin/projects', methods=['GET'])
@admin_required
def list_projects():
    projects = get_all_projects()
    return jsonify({"projects": projects})


@admin_bp.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@admin_required
def remove_user(user_id):
    if session.get("user_id") == user_id:
        return jsonify({"error": "You cannot delete yourself!"}), 400
        
    delete_user(user_id)
    return jsonify({"message": "User and all their data deleted successfully"})
