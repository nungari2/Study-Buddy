from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from models import db, Course
import os
from datetime import datetime

course_bp = Blueprint("course_bp", __name__)

# Folder for uploaded thumbnails
UPLOAD_FOLDER = "uploads/thumbnails"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


# ===== Helper Function =====
def allowed_file(filename):
    """Check if the uploaded file has a valid extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def course_to_dict(course):
    """Manually convert a Course object to dictionary."""
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "thumbnail": course.thumbnail,
        "is_active": course.is_active,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }


# ===== Create a Course =====
@course_bp.route("/courses", methods=["POST"])
def create_course():
    title = request.form.get("title")
    description = request.form.get("description")
    thumbnail = None

    if not title:
        return jsonify({"error": "Course title is required"}), 400

    # Handle thumbnail upload (optional)
    if "thumbnail" in request.files:
        file = request.files["thumbnail"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            thumbnail = file_path
        else:
            return jsonify({"error": "Invalid thumbnail file type"}), 400

    new_course = Course(
        title=title,
        description=description,
        thumbnail=thumbnail,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.session.add(new_course)
    db.session.commit()

    return jsonify({
        "message": "Course created successfully",
        "course": course_to_dict(new_course)
    }), 201


# ===== Get All Active Courses =====
@course_bp.route("/courses", methods=["GET"])
def get_courses():
    courses = Course.query.filter_by(is_active=True).all()
    return jsonify([course_to_dict(c) for c in courses]), 200


# ===== Get a Single Course =====
@course_bp.route("/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    course = Course.query.get(course_id)
    if not course or not course.is_active:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(course_to_dict(course)), 200


# ===== Update a Course =====
@course_bp.route("/courses/<int:course_id>", methods=["PATCH"])
def update_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    title = request.form.get("title", course.title)
    description = request.form.get("description", course.description)

    # Handle thumbnail update
    if "thumbnail" in request.files:
        file = request.files["thumbnail"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            course.thumbnail = file_path
        else:
            return jsonify({"error": "Invalid thumbnail file type"}), 400

    course.title = title
    course.description = description
    course.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "message": "Course updated successfully",
        "course": course_to_dict(course)
    }), 200


# ===== Soft Deactivate Course =====
@course_bp.route("/courses/<int:course_id>/deactivate", methods=["PATCH"])
def deactivate_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    course.is_active = False
    course.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": f"Course '{course.title}' deactivated successfully",
        "course": course_to_dict(course)
    }), 200


# ===== Reactivate Course =====
@course_bp.route("/courses/<int:course_id>/reactivate", methods=["PATCH"])
def reactivate_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    course.is_active = True
    course.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": f"Course '{course.title}' reactivated successfully",
        "course": course_to_dict(course)
    }), 200


# ===== Hard Delete Course =====
@course_bp.route("/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    db.session.delete(course)
    db.session.commit()

    return jsonify({"message": "Course permanently deleted"}), 200

