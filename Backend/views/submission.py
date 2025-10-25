from flask import Blueprint, request, jsonify
from models import db, Submission, Assignment, User
from datetime import datetime
import os

submission_bp = Blueprint("submission_bp", __name__)

UPLOAD_DIR = "uploads/submissions"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =====================  SUBMIT ASSIGNMENT =====================
@submission_bp.route("/submissions", methods=["POST"])
def submit_assignment():
    """Submit assignment as text or file (max 3 attempts per student per assignment)."""
    student_id = request.form.get("student_id")
    assignment_id = request.form.get("assignment_id")
    content = request.form.get("content")
    file = request.files.get("file")

    #  Required fields
    if not student_id or not assignment_id:
        return jsonify({"error": "student_id and assignment_id are required"}), 400

    #  Validate assignment
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    if not assignment.is_active:
        return jsonify({"error": "Assignment is not active"}), 400
    if not assignment.due_date:
        return jsonify({"error": "Assignment due_date not set"}), 400
    if datetime.utcnow() > assignment.due_date:
        return jsonify({"error": "Submission deadline has passed"}), 400

    #  Validate student
    student = User.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    #  Check number of attempts
    attempts = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).count()
    if attempts >= 3:
        return jsonify({"error": "You have reached the maximum of 3 submission attempts"}), 400

    #  Ensure there is content
    if not content and not file:
        return jsonify({"error": "You must submit either text content or a file"}), 400

    #  Handle file upload
    file_path = None
    if file:
        allowed_ext = {"pdf", "docx", "jpg", "jpeg", "png"}
        ext = file.filename.split(".")[-1].lower()
        if ext not in allowed_ext:
            return jsonify({"error": f"Invalid file type: {ext}"}), 400

        # Save file
        filename = f"student{student_id}_assignment{assignment_id}_attempt{attempts + 1}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        file.save(file_path)

    #  Create submission
    submission = Submission(
        student_id=student_id,
        assignment_id=assignment_id,
        content=content,
        file_path=file_path,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.session.add(submission)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Submission successful (Attempt {attempts + 1} of 3)",
        "submission": serialize_submission(submission)
    }), 201


# =====================  GET STUDENT'S SUBMISSION =====================
@submission_bp.route("/submissions/<int:assignment_id>/<int:student_id>", methods=["GET"])
def get_student_submission(assignment_id, student_id):
    """Get all submissions by a student for a specific assignment."""
    submissions = Submission.query.filter_by(assignment_id=assignment_id, student_id=student_id).all()
    if not submissions:
        return jsonify({"error": "No submissions found"}), 404

    return jsonify({
        "count": len(submissions),
        "submissions": [serialize_submission(s) for s in submissions]
    }), 200


# =====================  VIEW ALL SUBMISSIONS FOR AN ASSIGNMENT =====================
@submission_bp.route("/submissions/<int:assignment_id>/all", methods=["GET"])
def get_all_submissions(assignment_id):
    """View all student submissions for a given assignment (for instructor/admin)."""
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    if not submissions:
        return jsonify({"message": "No submissions for this assignment yet"}), 200

    return jsonify({
        "assignment": assignment.title,
        "total_submissions": len(submissions),
        "submissions": [serialize_submission(s) for s in submissions]
    }), 200


# =====================  HELPER =====================
def serialize_submission(submission):
    return {
        "id": submission.id,
        "student_id": submission.student_id,
        "assignment_id": submission.assignment_id,
        "content": submission.content,
        "file_path": submission.file_path,
        "created_at": submission.created_at.isoformat() if submission.created_at else None,
        "updated_at": submission.updated_at.isoformat() if submission.updated_at else None,
    }
