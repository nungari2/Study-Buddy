from flask import Blueprint, request, jsonify
from models import db, Grade, Submission, User, Assignment
from datetime import datetime
from openai import OpenAI
import os



client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

grade_bp = Blueprint("grade_bp", __name__)

# =========================
# CREATE A GRADE (Instructor)
# =========================
@grade_bp.route("/grades", methods=["POST"])
def create_grade():
    data = request.get_json()
    score = data.get("score")
    feedback = data.get("feedback")
    submission_id = data.get("submission_id")
    instructor_id = data.get("instructor_id")

    # --- Validation ---
    if score is None or submission_id is None or instructor_id is None:
        return jsonify({"error": "score, submission_id, and instructor_id are required"}), 400
    if not (0 <= score <= 100):
        return jsonify({"error": "Score must be between 0 and 100"}), 400

    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    instructor = User.query.get(instructor_id)
    if not instructor:
        return jsonify({"error": "Instructor not found"}), 404

    # --- Prevent duplicate grading ---
    existing_grade = Grade.query.filter_by(submission_id=submission_id).first()
    if existing_grade:
        return jsonify({"error": "This submission has already been graded"}), 400

    new_grade = Grade(
        score=score,
        feedback=feedback,
        submission_id=submission.id,
        instructor_id=instructor.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(new_grade)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Grade created successfully",
        "grade": serialize_grade(new_grade)
    }), 201


# =========================
# UPDATE GRADE
# =========================
@grade_bp.route("/grades/<int:grade_id>", methods=["PATCH"])
def update_grade(grade_id):
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({"error": "Grade not found"}), 404

    data = request.get_json()
    score = data.get("score")
    feedback = data.get("feedback")

    if score is not None:
        if not (0 <= score <= 100):
            return jsonify({"error": "Score must be between 0 and 100"}), 400
        grade.score = score
    if feedback:
        grade.feedback = feedback

    grade.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Grade updated successfully",
        "grade": serialize_grade(grade)
    })


# =========================
# GET GRADE FOR SUBMISSION (Student view)
# =========================
@grade_bp.route("/grades/submission/<int:submission_id>", methods=["GET"])
def get_grade_for_submission(submission_id):
    grade = Grade.query.filter_by(submission_id=submission_id).first()
    if not grade:
        return jsonify({"error": "Grade not found for this submission"}), 404
    return jsonify(serialize_grade(grade))


# =========================
# GET ALL GRADES (Instructor)
# =========================
@grade_bp.route("/grades/instructor/<int:instructor_id>", methods=["GET"])
def get_grades_by_instructor(instructor_id):
    grades = Grade.query.filter_by(instructor_id=instructor_id).all()
    return jsonify([serialize_grade(g) for g in grades])


# =========================
# DELETE GRADE
# =========================
@grade_bp.route("/grades/<int:grade_id>", methods=["DELETE"])
def delete_grade(grade_id):
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({"error": "Grade not found"}), 404

    db.session.delete(grade)
    db.session.commit()

    return jsonify({"success": True, "message": "Grade deleted successfully"})

# =========================
# AI GRADE
# =========================


@grade_bp.route("/grades/ai_suggest/<int:submission_id>", methods=["POST"])
def ai_suggest_grade(submission_id):
    """Generate AI-based grade suggestion (score + feedback)."""
    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    # Fetch assignment details (if linked)
    assignment = Assignment.query.get(submission.assignment_id)
    assignment_instructions = assignment.title + " - " + (assignment.description or "") if assignment else "No description provided."

    # Combine submission data
    content = submission.content or "No text content provided."
    file_path = submission.file_path or None

    # --- Construct prompt for OpenAI ---
    prompt = f"""
    You are an academic instructor grading a student's work.
    Here are the assignment details:
    {assignment_instructions}

    Student's submission:
    {content}

    Grade the submission fairly between 0 and 100 based on clarity, accuracy, completeness, and relevance.
    Respond in JSON with two fields:
    {{
        "suggested_score": <number between 0 and 100>,
        "feedback": "<brief constructive feedback>"
    }}
    """

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0.3
        )

        # Extract and parse JSON from OpenAI output
        ai_output = response.output[0].content[0].text.strip()

        # Try to parse JSON safely
        import json
        try:
            result = json.loads(ai_output)
        except json.JSONDecodeError:
            # fallback: if model responds with plain text
            result = {
                "suggested_score": None,
                "feedback": ai_output
            }

        return jsonify({
            "success": True,
            "ai_suggestion": result,
            "submission_id": submission_id
        })

    except Exception as e:
        return jsonify({"error": f"AI grading failed: {str(e)}"}), 500

# =========================
# SERIALIZER
# =========================
def serialize_grade(grade):
    return {
        "id": grade.id,
        "score": grade.score,
        "feedback": grade.feedback,
        "submission": {
            "id": grade.submission.id,
            "student_id": grade.submission.student_id
        },
        "instructor": {
            "id": grade.instructor.id,
            "name": getattr(grade.instructor, "name", "Unknown")
        },
        "created_at": grade.created_at.isoformat() if grade.created_at else None,
        "updated_at": grade.updated_at.isoformat() if grade.updated_at else None
    }
