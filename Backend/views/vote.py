from flask import Blueprint, request, jsonify
from models import db, Vote, Answer, User

vote_bp = Blueprint("vote_bp", __name__)

# ==========================================================
# 1️ CREATE OR TOGGLE A VOTE
# ==========================================================
@vote_bp.route("/votes/<int:answer_id>", methods=["POST"])
def vote_answer(answer_id):
    data = request.get_json()
    user_id = data.get("user_id")
    vote_type = data.get("vote_type")  # "up" or "down"

    if not all([user_id, vote_type]):
        return jsonify({"error": "user_id and vote_type are required"}), 400
    if vote_type not in ["up", "down"]:
        return jsonify({"error": "vote_type must be 'up' or 'down'"}), 400

    answer = Answer.query.get(answer_id)
    if not answer:
        return jsonify({"error": "Answer not found"}), 404

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check if vote exists
    existing_vote = Vote.query.filter_by(user_id=user_id, answer_id=answer_id).first()

    if existing_vote:
        # Toggle or switch
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
            db.session.commit()
            return jsonify({"message": f"{vote_type}vote removed."}), 200
        else:
            existing_vote.vote_type = vote_type
            db.session.commit()
            return jsonify({"message": f"Vote changed to {vote_type}vote."}), 200
    else:
        new_vote = Vote(user_id=user_id, answer_id=answer_id, vote_type=vote_type)
        db.session.add(new_vote)
        db.session.commit()
        return jsonify({"message": f"{vote_type}vote added successfully."}), 201


# ==========================================================
# 2️ GET TOTAL VOTES FOR AN ANSWER
# ==========================================================
@vote_bp.route("/votes/<int:answer_id>", methods=["GET"])
def get_votes(answer_id):
    answer = Answer.query.get(answer_id)
    if not answer:
        return jsonify({"error": "Answer not found"}), 404

    upvotes = Vote.query.filter_by(answer_id=answer_id, vote_type="up").count()
    downvotes = Vote.query.filter_by(answer_id=answer_id, vote_type="down").count()

    return jsonify({
        "answer_id": answer_id,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "total_score": upvotes - downvotes
    }), 200


# ==========================================================
# 3️ REMOVE A USER'S VOTE
# ==========================================================
@vote_bp.route("/votes/<int:answer_id>", methods=["DELETE"])
def remove_vote(answer_id):
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    vote = Vote.query.filter_by(answer_id=answer_id, user_id=user_id).first()
    if not vote:
        return jsonify({"error": "No vote found for this user"}), 404

    db.session.delete(vote)
    db.session.commit()
    return jsonify({"message": "Vote removed successfully"}), 200


# ==========================================================
# 4️ GET TOP ANSWERS BY SCORE (Upvotes - Downvotes)
# ==========================================================
@vote_bp.route("/votes/top-answers", methods=["GET"])
def get_top_answers():
    """
    Returns all answers sorted by total vote score (up - down).
    Optionally filter by question_id using ?question_id=1
    """
    question_id = request.args.get("question_id", type=int)

    query = Answer.query
    if question_id:
        query = query.filter_by(question_id=question_id)

    answers = query.all()

    data = []
    for a in answers:
        upvotes = Vote.query.filter_by(answer_id=a.id, vote_type="up").count()
        downvotes = Vote.query.filter_by(answer_id=a.id, vote_type="down").count()
        score = upvotes - downvotes

        data.append({
            "answer_id": a.id,
            "question_id": a.question_id,
            "author_id": a.author_id,
            "body": a.body,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "score": score
        })

    # Sort answers by highest score first
    data = sorted(data, key=lambda x: x["score"], reverse=True)

    return jsonify({
        "success": True,
        "total_answers": len(data),
        "answers": data
    }), 200
