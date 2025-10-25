from flask import Blueprint, jsonify
from models import db, Note, Flashcard
from datetime import datetime
from openai import OpenAI
import os, json, re

flashcard_bp = Blueprint("flashcard_bp", __name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Helper Function: Extract JSON safely =====
def extract_json(text):
    """Try to extract a valid JSON array from the AI response text."""
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            return json.loads(text)
    except Exception as e:
        print("JSON parse error:", e)
        return None


# ===== Route: Generate Flashcards =====
@flashcard_bp.route("/flashcards/generate/<int:note_id>", methods=["POST"])
def generate_flashcards(note_id):
    """Generate multiple-choice flashcards from a note using OpenAI."""
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    # 1️ Ensure the note has text content
    if not note.content:
        return jsonify({"error": "Note has no text content"}), 400

    text = note.content

    # 2️ AI Prompt for multiple-choice flashcards
    prompt = f"""
    Generate 5 multiple-choice flashcards from this note.
    Each flashcard must be in this exact JSON format:
    [
      {{
        "question": "What is ...?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "Option B"
      }}
    ]

    Text:
    {text}
    """

    try:
        # 3️ Send to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        ai_output = response.choices[0].message.content.strip()
        print("\n=== AI OUTPUT ===\n", ai_output)

        # 4️ Parse JSON safely
        flashcards_data = extract_json(ai_output)
        if not flashcards_data:
            return jsonify({"error": "Failed to parse AI response"}), 500

    except Exception as e:
        # print("OpenAI error:", e)
        return jsonify({"error": "Failed to generate flashcards"}), 500

    # 5️⃣ Save generated flashcards to database (avoid duplicates)
    generated_flashcards = []
    for fc in flashcards_data:
        question = fc.get("question")
        answer = fc.get("answer")
        options = fc.get("options")

        if not (question and answer and options):
            continue

        # Skip duplicates
        existing = Flashcard.query.filter_by(note_id=note.id, question=question).first()
        if existing:
            continue

        new_fc = Flashcard(
            question=question,
            answer=answer,
            options=options,  # multiple-choice options
            note_id=note.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.session.add(new_fc)
        generated_flashcards.append(new_fc)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"{len(generated_flashcards)} flashcards generated successfully.",
        "flashcards": [serialize_flashcard(fc) for fc in generated_flashcards],
    }), 201


# ===== Serializer =====
def serialize_flashcard(fc):
    """Convert Flashcard model to JSON."""
    return {
        "id": fc.id,
        "question": fc.question,
        "options": fc.options or [],
        "answer": fc.answer,
        "note_id": fc.note_id,
        "created_at": fc.created_at.isoformat() if fc.created_at else None,
    }

