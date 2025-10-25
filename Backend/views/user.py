from flask import Blueprint, request, jsonify, current_app, url_for
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from mimetypes import guess_type

user_bp = Blueprint("user_bp", __name__)

# ===== File Upload Config =====
UPLOAD_FOLDER = os.path.join("static", "uploads", "profiles")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ===== Helper Functions =====
def allowed_file(file):
    """Ensure file is a valid image by checking extension and MIME type."""
    filename = file.filename
    if not ("." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS):
        return False

    mime_type, _ = guess_type(filename)
    return mime_type and mime_type.startswith("image/")


# ===== Register User =====
@user_bp.route("/users", methods=["POST"])
def create_user():
    """Register a new user"""
    data = request.form if request.form else request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    hashed_pw = generate_password_hash(password)

    new_user = User(
        username=username,
        email=email,
        password=hashed_pw,
        role=role
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "success": "User registered successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "created_at": new_user.created_at.isoformat()
        }
    }), 201


# ===== Login =====
@user_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user"""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "bio": user.bio,
            "profile_picture": (
                url_for("static", filename=user.profile_picture, _external=True)
                if user.profile_picture else None
            )
        }
    }), 200


# ===== Get User Profile =====
@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Retrieve a user's profile"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "bio": user.bio,
        "profile_picture": (
            url_for("static", filename=user.profile_picture, _external=True)
            if user.profile_picture else None
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if hasattr(user, "updated_at") and user.updated_at else None
    }), 200


# ===== Update Profile =====
@user_bp.route("/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    """Update a user's profile"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.form
    file = request.files.get("profile_picture")
    remove_picture = data.get("remove_picture")

    # Update text fields
    user.bio = data.get("bio", user.bio)
    user.updated_at = datetime.utcnow()

    # Handle password change
    if data.get("password"):
        user.password = generate_password_hash(data["password"])

    # Handle removing picture
    if remove_picture == "true":
        if user.profile_picture:
            abs_path = os.path.join(current_app.root_path, "static", user.profile_picture)
            if os.path.exists(abs_path):
                os.remove(abs_path)
        user.profile_picture = None

    # Handle picture upload
    elif file:
        if not allowed_file(file):
            return jsonify({"error": "Invalid file type. Only image files are allowed."}), 400

        if len(file.read()) > MAX_CONTENT_LENGTH:
            return jsonify({"error": "File too large. Maximum size is 2MB."}), 400

        file.seek(0)  # Reset file cursor after reading size check
        filename = secure_filename(f"{user.id}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        user.profile_picture = os.path.join("uploads", "profiles", filename)

    db.session.commit()

    return jsonify({
        "success": "Profile updated successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "bio": user.bio,
            "role": user.role,
            "profile_picture": (
                url_for("static", filename=user.profile_picture, _external=True)
                if user.profile_picture else None
            ),
            "updated_at": user.updated_at.isoformat()
        }
    }), 200


# ===== Delete User =====
@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user account"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Delete profile picture file if it exists
    if user.profile_picture:
        abs_path = os.path.join(current_app.root_path, "static", user.profile_picture)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    db.session.delete(user)
    db.session.commit()

    return jsonify({"success": "User deleted successfully"}), 200
