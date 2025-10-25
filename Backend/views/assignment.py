from flask import Blueprint, request, jsonify
from models import db, Assignment, Unit
from datetime import datetime
import os
from werkzeug.utils import secure_filename

assignment_bp = Blueprint("assignment_bp", __name__)

UPLOAD_FOLDER = "uploads/assignments"
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "zip"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_due_date(due_date_str):
    """
    Try to parse ISO formatted date/time.
    Accepts e.g. "2025-10-31T23:59:00" or "2025-10-31".
    Returns datetime or raises ValueError.
    """
    # datetime.fromisoformat handles both date and datetime strings in Python 3.8+
    return datetime.fromisoformat(due_date_str)


# ===============================
# CREATE ASSIGNMENT
# ===============================
@assignment_bp.route("/assignments", methods=["POST"])
def create_assignment():
    """
    Create assignment:
      - required fields: title, unit_id, due_date
      - optional: description, file
      - prevents duplicate (same title in same unit, active)
    """
    # prefer form data (for file uploads); fallback to json
    data = request.form if request.form else request.get_json() or {}
    title = data.get("title")
    description = data.get("description")
    due_date_str = data.get("due_date")
    unit_id = data.get("unit_id")
    file = request.files.get("file")

    # -----------------------
    # Basic validation
    # -----------------------
    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not unit_id:
        return jsonify({"error": "unit_id is required"}), 400
    if not due_date_str:
        return jsonify({"error": "due_date is required and must be in ISO format (e.g. 2025-10-31T23:59:00)"}), 400

    # ensure unit exists
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    # parse due date
    try:
        due_date = parse_due_date(due_date_str)
    except Exception:
        return jsonify({"error": "Invalid due_date format. Use ISO format like 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS'."}), 400

    # prevent duplicate active assignment with same title in same unit
    duplicate = Assignment.query.filter_by(title=title.strip(), unit_id=unit.id, is_active=True).first()
    if duplicate:
        return jsonify({"error": "An active assignment with the same title already exists for this unit."}), 400

    # -----------------------
    # File validation (only if file provided)
    # -----------------------
    file_path = None
    if file:
        if not allowed_file(file.filename):
            return jsonify({"error": f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400
        # prepare filename (prefix timestamp to avoid collisions)
        filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        # save file after validations
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(file_path)

    # -----------------------
    # Create assignment
    # -----------------------
    new_assignment = Assignment(
        title=title.strip(),
        description=description,
        due_date=due_date,
        file_path=file_path,
        unit_id=unit.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True
    )

    db.session.add(new_assignment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Assignment created successfully",
        "assignment": {
            "id": new_assignment.id,
            "title": new_assignment.title,
            "description": new_assignment.description,
            "due_date": new_assignment.due_date.isoformat() if new_assignment.due_date else None,
            "file_path": new_assignment.file_path,
            "unit_id": new_assignment.unit_id,
            "is_active": new_assignment.is_active,
            "created_at": new_assignment.created_at.isoformat() if new_assignment.created_at else None
        }
    }), 201



# ===============================
# GET ALL ASSIGNMENTS
# ===============================
@assignment_bp.route("/assignments", methods=["GET"])
def get_all_assignments():
    """View all active assignments."""
    assignments = Assignment.query.filter_by(is_active=True).all()
    return jsonify([serialize_assignment(a) for a in assignments]), 200


# ===============================
# GET ASSIGNMENTS BY UNIT
# ===============================
@assignment_bp.route("/assignments/unit/<int:unit_id>", methods=["GET"])
def get_assignments_by_unit(unit_id):
    """Fetch all assignments for a specific unit."""
    assignments = Assignment.query.filter_by(unit_id=unit_id, is_active=True).all()
    if not assignments:
        return jsonify({"message": "No assignments found for this unit"}), 404
    return jsonify([serialize_assignment(a) for a in assignments]), 200


# ===============================
# GET SINGLE ASSIGNMENT
# ===============================
@assignment_bp.route("/assignments/<int:assignment_id>", methods=["GET"])
def get_assignment(assignment_id):
    """Fetch details for a specific assignment."""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    return jsonify(serialize_assignment(assignment)), 200


# ===============================
# UPDATE ASSIGNMENT
# ===============================
@assignment_bp.route("/assignments/<int:assignment_id>", methods=["PATCH"])
def update_assignment(assignment_id):
    """Update assignment details or replace file."""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    data = request.form
    file = request.files.get("file")

    # Update text fields
    assignment.title = data.get("title", assignment.title)
    assignment.description = data.get("description", assignment.description)

    # Update due date if provided
    if data.get("due_date"):
        try:
            assignment.due_date = datetime.fromisoformat(data.get("due_date"))
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    # Replace file if uploaded
    if file:
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        assignment.file_path = path

    assignment.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Assignment updated successfully",
        "assignment": serialize_assignment(assignment)
    }), 200


@assignment_bp.route("/assignments/<int:assignment_id>/toggle", methods=["PATCH"])
def toggle_assignment(assignment_id):
    """Toggle assignment active/inactive status"""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    # Flip active status
    assignment.is_active = not assignment.is_active
    db.session.commit()

    status = "activated" if assignment.is_active else "deactivated"

    return jsonify({
        "success": True,
        "message": f"Assignment {status} successfully",
        "is_active": assignment.is_active
    }), 200



# ===============================
# SERIALIZER
# ===============================
def serialize_assignment(a):
    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "file_path": a.file_path,
        "unit_id": a.unit_id,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None
    }
