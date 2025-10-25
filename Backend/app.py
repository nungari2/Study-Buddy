from flask import Flask
from models import db 
from flask_migrate import Migrate
from dotenv import load_dotenv
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

migrate = Migrate(app, db)
db.init_app(app)

load_dotenv()
# print("API KEY LOADED:", os.getenv("OPENAI_API_KEY"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#Register Blueprints
from views import *

app.register_blueprint(user_bp)
app.register_blueprint(course_bp)
app.register_blueprint(unit_bp)
app.register_blueprint(note_bp)
app.register_blueprint(flashcard_bp)
app.register_blueprint(assignment_bp)
app.register_blueprint(submission_bp)
app.register_blueprint(grade_bp)
app.register_blueprint(question_bp)
app.register_blueprint(answer_bp)
app.register_blueprint(vote_bp)




if __name__ == "__main__":
    app.run(debug=True)