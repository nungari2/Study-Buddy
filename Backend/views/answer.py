from flask import Blueprint, request, jsonify
from models import db, Answer, Question, User
from datetime import datetime

answer_bp = Blueprint("answer_bp", __name__)

# ==========================================================
# 1️ CREATE AN ANSWER
# ==========================================================
@answer_bp.route("/answers", methods=["POST"])
def create_answer():
    data = request.get_json()

    body = data.get("body")
    question_id = data.get("question_id")
    author_id = data.get("author_id")

    # Validation
    if not all([body, question_id, author_id]):
        return jsonify({"error": "body, question_id, and author_id are required"}), 400

    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    author = User.query.get(author_id)
    if not author:
        return jsonify({"error": "Author not found"}), 404

    # Create new answer
    new_answer = Answer(
        body=body,
        question_id=question.id,
        author_id=author.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.session.add(new_answer)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Answer posted successfully",
        "answer": serialize_answer(new_answer)
    }), 201


# ==========================================================
# 2️ GET ALL ANSWERS FOR A QUESTION
# ==========================================================
@answer_bp.route("/questions/<int:question_id>/answers", methods=["GET"])
def get_answers_for_question(question_id):
    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    answers = Answer.query.filter_by(question_id=question_id).order_by(Answer.created_at.desc()).all()
    return jsonify([serialize_answer(a) for a in answers]), 200


# ==========================================================
# 3️ UPDATE AN ANSWER (ONLY BY AUTHOR)
# ==========================================================
@answer_bp.route("/answers/<int:answer_id>", methods=["PATCH"])
def update_answer(answer_id):
    data = request.get_json()
    author_id = data.get("author_id")
    new_body = data.get("body")

    if not author_id:
        return jsonify({"error": "author_id is required"}), 400
    if not new_body:
        return jsonify({"error": "New answer text (body) is required"}), 400

    answer = Answer.query.get(answer_id)
    if not answer:
        return jsonify({"error": "Answer not found"}), 404

    # Only author can update
    if answer.author_id != author_id:
        return jsonify({"error": "You can only edit your own answer."}), 403

    answer.body = new_body
    answer.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Answer updated successfully",
        "answer": serialize_answer(answer)
    }), 200


# ==========================================================
# 4️ DELETE AN ANSWER (ONLY BY AUTHOR)
# ==========================================================
@answer_bp.route("/answers/<int:answer_id>", methods=["DELETE"])
def delete_answer(answer_id):
    data = request.get_json(silent=True) or {}
    author_id = data.get("author_id") or request.args.get("author_id", type=int)

    if not author_id:
        return jsonify({"error": "author_id is required"}), 400

    answer = Answer.query.get(answer_id)
    if not answer:
        return jsonify({"error": "Answer not found"}), 404

    if answer.author_id != author_id:
        return jsonify({"error": "You can only delete your own answer."}), 403

    db.session.delete(answer)
    db.session.commit()

    return jsonify({"success": True, "message": "Answer deleted successfully"}), 200


# ==========================================================
# 🔹 Helper: Serialize Answer
# ==========================================================
def serialize_answer(answer):
    return {
        "id": answer.id,
        "body": answer.body,
        "question": {
            "id": answer.question.id,
            "title": answer.question.title
        },
        "author": {
            "id": answer.author.id,
            "name": getattr(answer.author, "name", None)
        },
        "created_at": answer.created_at.isoformat() if answer.created_at else None,
        "updated_at": answer.updated_at.isoformat() if answer.updated_at else None
    }
