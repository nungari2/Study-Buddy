from flask import Blueprint, request, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
from models import db, Note, Unit, User
from datetime import datetime
import os

note_bp = Blueprint("note_bp", __name__)

# ---------------------------
# File Upload Config
# ---------------------------
UPLOAD_FOLDER = "static/notes"
ALLOWED_EXTENSIONS = {"pdf"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if uploaded file has a valid extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------
@note_bp.route("/notes", methods=["POST"])
def create_note():
    content = request.form.get("content")
    unit_id = request.form.get("unit_id")
    uploaded_by = request.form.get("uploaded_by")
    file = request.files.get("pdf_file")

    # Validation
    if not unit_id or not uploaded_by:
        return jsonify({"error": "unit_id and uploaded_by are required"}), 400
    if not content and not file:
        return jsonify({"error": "Either text content or a PDF file is required"}), 400

    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    uploader = User.query.get(uploaded_by)
    if not uploader:
        return jsonify({"error": "Uploader (user) not found"}), 404

    # Check for duplicate content or file in the same unit
    if content:
        existing_content = Note.query.filter_by(unit_id=unit.id, content=content).first()
        if existing_content:
            return jsonify({"error": "A note with the same content already exists in this unit."}), 400

    file_path = None
    if file:
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # Check for duplicate filename in same unit
        existing_file = Note.query.filter_by(unit_id=unit.id, file_path=file_path).first()
        if existing_file:
            return jsonify({"error": "A note with the same PDF already exists in this unit."}), 400

        # Save file
        file.save(file_path)

    new_note = Note(
        content=content,
        file_path=file_path,
        unit_id=unit.id,
        uploaded_by=uploader.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.session.add(new_note)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Note created successfully",
        "note": serialize_note(new_note)
    }), 201



# ---------------------------
# GET ALL NOTES (optional filters)
# ---------------------------
@note_bp.route("/notes", methods=["GET"])
def get_all_notes():
    unit_id = request.args.get("unit_id")
    uploaded_by = request.args.get("uploaded_by")

    query = Note.query
    if unit_id:
        query = query.filter_by(unit_id=unit_id)
    if uploaded_by:
        query = query.filter_by(uploaded_by=uploaded_by)

    notes = query.all()
    if not notes:
        return jsonify({"message": "No notes found"}), 404

    return jsonify([serialize_note(note) for note in notes])


# ---------------------------
# GET SINGLE NOTE
# ---------------------------
@note_bp.route("/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404
    return jsonify(serialize_note(note))


# ---------------------------
# DOWNLOAD NOTE PDF
# ---------------------------
@note_bp.route("/notes/<int:note_id>/download", methods=["GET"])
def download_note_pdf(note_id):
    note = Note.query.get(note_id)
    if not note or not note.file_path:
        return jsonify({"error": "No PDF available for this note"}), 404

    directory = os.path.dirname(note.file_path)
    filename = os.path.basename(note.file_path)
    return send_from_directory(directory, filename, as_attachment=True)


# ---------------------------
# UPDATE NOTE
# ---------------------------
@note_bp.route("/notes/<int:note_id>", methods=["PATCH"])
def update_note(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    content = request.form.get("content")
    unit_id = request.form.get("unit_id")
    uploaded_by = request.form.get("uploaded_by")
    file = request.files.get("pdf_file")

    if content:
        note.content = content
    if unit_id and Unit.query.get(unit_id):
        note.unit_id = unit_id
    if uploaded_by and User.query.get(uploaded_by):
        note.uploaded_by = uploaded_by
    if file:
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        note.file_path = file_path

    note.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Note updated successfully",
        "note": serialize_note(note)
    })


# ---------------------------
# TOGGLE NOTE ACTIVE/INACTIVE
# ---------------------------
@note_bp.route("/notes/<int:note_id>/toggle-active", methods=["PATCH"])
def toggle_note_active(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    note.is_active = not note.is_active
    db.session.commit()

    status = "activated" if note.is_active else "deactivated"
    return jsonify({"success": f"Note {status} successfully"})


# ---------------------------
# DELETE NOTE
# ---------------------------
@note_bp.route("/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    db.session.delete(note)
    db.session.commit()
    return jsonify({"success": True, "message": "Note deleted successfully"})


# ---------------------------
# Helper: Serialize Note
# ---------------------------
def serialize_note(note):
    """Return a clean JSON structure for each note."""
    pdf_url = None
    if note.file_path and os.path.exists(note.file_path):
        pdf_url = url_for("note_bp.download_note_pdf", note_id=note.id, _external=True)

    return {
        "id": note.id,
        "content": note.content,
        "pdf_url": pdf_url,
        "is_active": note.is_active,
        "unit": {
            "id": note.unit.id,
            "title": note.unit.title,
            "course": {
                "id": note.unit.course.id,
                "title": note.unit.course.title
            }
        },
        "uploaded_by": note.uploader.id if note.uploader else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None
    }
