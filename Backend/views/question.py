from flask import Blueprint, request, jsonify
from models import db, Question, User
from datetime import datetime

question_bp = Blueprint("question_bp", __name__)

# =========================
# CREATE QUESTION
# =========================
@question_bp.route("/questions", methods=["POST"])
def create_question():
    data = request.get_json()
    title = data.get("title")
    body = data.get("body")
    author_id = data.get("author_id")

    if not title or not body or not author_id:
        return jsonify({"error": "Title, body, and author_id are required"}), 400

    # Check if author exists
    author = User.query.get(author_id)
    if not author:
        return jsonify({"error": "Author not found"}), 404

    # Prevent duplicate question titles by same author
    existing = Question.query.filter_by(title=title, author_id=author_id).first()
    if existing:
        return jsonify({"error": "You already asked a question with this title."}), 400

    question = Question(
        title=title,
        body=body,
        author_id=author_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.session.add(question)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Question created successfully",
        "question": serialize_question(question)
    }), 201


# =========================
# GET ALL QUESTIONS
# =========================
@question_bp.route("/questions", methods=["GET"])
def get_all_questions():
    questions = Question.query.order_by(Question.created_at.desc()).all()
    return jsonify([serialize_question(q) for q in questions]), 200


# =========================
# GET SINGLE QUESTION
# =========================
@question_bp.route("/questions/<int:question_id>", methods=["GET"])
def get_question(question_id):
    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404
    return jsonify(serialize_question(question)), 200


# =========================
# GET QUESTIONS BY AUTHOR
# =========================
@question_bp.route("/questions/author/<int:author_id>", methods=["GET"])
def get_questions_by_author(author_id):
    questions = Question.query.filter_by(author_id=author_id).order_by(Question.created_at.desc()).all()
    return jsonify([serialize_question(q) for q in questions]), 200


# =========================
# UPDATE QUESTION
# =========================
@question_bp.route("/questions/<int:question_id>", methods=["PATCH"])
def update_question(question_id):
    data = request.get_json()
    title = data.get("title")
    body = data.get("body")
    author_id = data.get("author_id")

    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    # Authorization check
    if question.author_id != author_id:
        return jsonify({"error": "You can only update your own questions."}), 403

    if title:
        question.title = title
    if body:
        question.body = body

    question.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Question updated successfully",
        "question": serialize_question(question)
    }), 200


# =========================
# DELETE QUESTION
# =========================
@question_bp.route("/questions/<int:question_id>", methods=["DELETE"])
def delete_question(question_id):
    # Try to get JSON or fallback to query parameters
    data = request.get_json(silent=True) or {}
    author_id = data.get("author_id") or request.args.get("author_id", type=int)

    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    # Require author_id to verify permission
    if not author_id:
        return jsonify({"error": "author_id is required"}), 400

    # Allow delete only by author (future: add admin override)
    if question.author_id != author_id:
        return jsonify({"error": "You can only delete your own question."}), 403

    db.session.delete(question)
    db.session.commit()

    return jsonify({"success": True, "message": "Question deleted successfully"}), 200


# =========================
# HELPER — SERIALIZER
# =========================
def serialize_question(q):
    return {
        "id": q.id,
        "title": q.title,
        "body": q.body,
        "author_id": q.author_id,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        "answers_count": len(q.answers)
    }
