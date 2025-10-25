from flask import Blueprint, request, jsonify
from models import db, Unit, Course, User

unit_bp = Blueprint("unit_bp", __name__)

# =========================
# CREATE A UNIT
# =========================
@unit_bp.route("/units", methods=["POST"])
def create_unit():
    data = request.get_json()
    title = data.get("title")
    overview = data.get("overview")
    course_id = data.get("course_id")
    instructor_id = data.get("instructor_id")

    # Validate required fields
    if not all([title, course_id, instructor_id]):
        return jsonify({"error": "Title, course_id, and instructor_id are required"}), 400

    # Check if course exists
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # Check if instructor exists
    instructor = User.query.get(instructor_id)
    if not instructor:
        return jsonify({"error": "Instructor not found"}), 404

    # Prevent duplicate unit title within the same course
    existing_unit = Unit.query.filter_by(title=title, course_id=course_id).first()
    if existing_unit:
        return jsonify({"error": f"A unit titled '{title}' already exists in this course."}), 400

    # Create new unit
    new_unit = Unit(
        title=title,
        overview=overview,
        course_id=course_id,
        instructor_id=instructor_id
    )
    db.session.add(new_unit)
    db.session.commit()

    return jsonify({
        "success": "Unit created successfully",
        "unit": {
            "id": new_unit.id,
            "title": new_unit.title,
            "overview": new_unit.overview,
            "course_id": new_unit.course_id,
            "instructor_id": new_unit.instructor_id,
            "is_active": new_unit.is_active
        }
    }), 201


# =========================
# GET ALL UNITS (OPTIONAL FILTER BY COURSE)
# =========================
@unit_bp.route("/units", methods=["GET"])
def get_units():
    course_id = request.args.get("course_id")
    instructor_id = request.args.get("instructor_id")

    query = Unit.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    if instructor_id:
        query = query.filter_by(instructor_id=instructor_id)

    units = query.all()
    if not units:
        return jsonify({"message": "No units found"}), 404

    return jsonify([
        {
            "id": u.id,
            "title": u.title,
            "overview": u.overview,
            "course_id": u.course_id,
            "instructor_id": u.instructor_id,
            "is_active": u.is_active
        } for u in units
    ])


# =========================
# GET SINGLE UNIT
# =========================
@unit_bp.route("/units/<int:unit_id>", methods=["GET"])
def get_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    return jsonify({
        "id": unit.id,
        "title": unit.title,
        "overview": unit.overview,
        "course_id": unit.course_id,
        "instructor_id": unit.instructor_id,
        "is_active": unit.is_active
    })


# =========================
# UPDATE UNIT
# =========================
@unit_bp.route("/units/<int:unit_id>", methods=["PATCH"])
def update_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    data = request.get_json()
    new_title = data.get("title", unit.title)
    new_overview = data.get("overview", unit.overview)
    new_instructor_id = data.get("instructor_id", unit.instructor_id)
    new_is_active = data.get("is_active", unit.is_active)

    # Prevent duplicate titles on update
    duplicate_unit = Unit.query.filter_by(title=new_title, course_id=unit.course_id).first()
    if duplicate_unit and duplicate_unit.id != unit.id:
        return jsonify({"error": f"A unit titled '{new_title}' already exists in this course."}), 400

    unit.title = new_title
    unit.overview = new_overview
    unit.instructor_id = new_instructor_id
    unit.is_active = new_is_active

    db.session.commit()

    return jsonify({
        "success": "Unit updated successfully",
        "updated_unit": {
            "id": unit.id,
            "title": unit.title,
            "overview": unit.overview,
            "course_id": unit.course_id,
            "instructor_id": unit.instructor_id,
            "is_active": unit.is_active
        }
    })


# =========================
# DEACTIVATE / ACTIVATE UNIT
# =========================
@unit_bp.route("/units/<int:unit_id>/toggle-active", methods=["PATCH"])
def toggle_unit_status(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    unit.is_active = not unit.is_active
    db.session.commit()

    status = "activated" if unit.is_active else "deactivated"
    return jsonify({"success": f"Unit {status} successfully"})


# =========================
# DELETE UNIT
# =========================
@unit_bp.route("/units/<int:unit_id>", methods=["DELETE"])
def delete_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    db.session.delete(unit)
    db.session.commit()
    return jsonify({"success": "Unit deleted successfully"})

