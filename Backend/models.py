from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import MetaData, event
from sqlalchemy.orm import validates

# For Alembic migration compatibility
metadata = MetaData()
db = SQLAlchemy(metadata=metadata)

# =========================================================
# Base Mixin (used by all models)
# =========================================================
class BaseModel:
    """Reusable fields for all models."""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"


# =========================================================
# User Model
# =========================================================
class User(db.Model, BaseModel):
    __tablename__ = "users"

    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="student")  # student | instructor | admin
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    units = db.relationship("Unit", back_populates="instructor", cascade="all, delete-orphan")
    questions = db.relationship("Question", back_populates="author", cascade="all, delete-orphan")
    answers = db.relationship("Answer", back_populates="author", cascade="all, delete-orphan")
    submissions = db.relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    given_grades = db.relationship("Grade", back_populates="instructor", foreign_keys="Grade.instructor_id")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    votes = db.relationship("Vote", back_populates="user", cascade="all, delete-orphan")


# =========================================================
# Course, Unit, Note, Flashcard
# =========================================================
class Course(db.Model, BaseModel):
    __tablename__ = "courses"

    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    thumbnail = db.Column(db.String(255))  # Optional image for the course
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    units = db.relationship("Unit", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course {self.title} active={self.is_active}>"


class Unit(db.Model, BaseModel):
    __tablename__ = "units"

    title = db.Column(db.String(120), nullable=False)
    overview = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False) 

    # Relationships
    course = db.relationship("Course", back_populates="units")
    instructor = db.relationship("User", back_populates="units")
    notes = db.relationship("Note", back_populates="unit", cascade="all, delete-orphan")
    assignments = db.relationship("Assignment", back_populates="unit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Unit {self.title} active={self.is_active}>"


class Note(db.Model, BaseModel):
    __tablename__ = "notes"

    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    unit = db.relationship("Unit", back_populates="notes")
    uploader = db.relationship("User")
    flashcards = db.relationship("Flashcard", back_populates="note", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Note id={self.id} unit_id={self.unit_id} active={self.is_active}>"


class Flashcard(db.Model, BaseModel):
    __tablename__ = "flashcards"

    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.String(255), nullable=False)
    options = db.Column(db.JSON) 
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=False)

    note = db.relationship("Note", back_populates="flashcards")


# =========================================================
# Discussion: Questions, Answers
# =========================================================
class Question(db.Model, BaseModel):
    __tablename__ = "questions"

    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    author = db.relationship("User", back_populates="questions")
    answers = db.relationship("Answer", back_populates="question", cascade="all, delete-orphan")

class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey("answers.id"), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # "up" or "down"

    user = db.relationship("User", back_populates="votes")
    answer = db.relationship("Answer", back_populates="votes")


class Answer(db.Model, BaseModel):
    __tablename__ = "answers"

    body = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_best = db.Column(db.Boolean, default=False)

    question = db.relationship("Question", back_populates="answers")
    author = db.relationship("User", back_populates="answers")
    votes = db.relationship("Vote", back_populates="answer", cascade="all, delete-orphan")



# =========================================================
# Assignments, Submissions, Grades
# =========================================================
class Assignment(db.Model, BaseModel):
    __tablename__ = "assignments"

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    file_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)

    # Relationships
    unit = db.relationship("Unit", back_populates="assignments")
    submissions = db.relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Assignment {self.title} active={self.is_active}>"


class Submission(db.Model, BaseModel):
    __tablename__ = "submissions"

    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)

    student = db.relationship("User", back_populates="submissions")
    assignment = db.relationship("Assignment", back_populates="submissions")
    grade = db.relationship("Grade", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class Grade(db.Model, BaseModel):
    __tablename__ = "grades"

    score = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    submission = db.relationship("Submission", back_populates="grade")
    instructor = db.relationship("User", back_populates="given_grades")


# =========================================================
# Notifications (system messages)
# =========================================================
class Notification(db.Model, BaseModel):
    __tablename__ = "notifications"

    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", back_populates="notifications")


# =========================================================
# Activity Log (for auditing who did what)
# =========================================================
class ActivityLog(db.Model, BaseModel):
    __tablename__ = "activity_logs"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(255), nullable=False)
    target_type = db.Column(db.String(50))  # e.g., 'Course', 'Note', 'Assignment'
    target_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))

    user = db.relationship("User", back_populates="activity_logs")


# =========================================================
# Automatic timestamp updates for parents
# =========================================================
def touch(mapper, connection, target):
    """Auto-update parent timestamps when child changes."""
    if hasattr(target, "unit") and target.unit:
        target.unit.updated_at = datetime.utcnow()
    elif hasattr(target, "course") and target.course:
        target.course.updated_at = datetime.utcnow()
    elif hasattr(target, "assignment") and target.assignment:
        target.assignment.updated_at = datetime.utcnow()


for model in [Note, Flashcard, Assignment, Submission, Grade]:
    event.listen(model, "after_insert", touch)
    event.listen(model, "after_update", touch)
    event.listen(model, "after_delete", touch)


