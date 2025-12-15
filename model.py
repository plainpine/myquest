from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    choice1 = db.Column(db.String(200))
    choice2 = db.Column(db.String(200))
    choice3 = db.Column(db.String(200))
    choice4 = db.Column(db.String(200))
    correct = db.Column(db.Integer)  # 正解番号（1〜4）
    category = db.Column(db.String(50))  # section / practice など
    explanation = db.Column(db.Text, nullable=True) # New field for explanation
    document_url = db.Column(db.String(500), nullable=True) # New field for document URL

    # TestResult との関連付け
    results = db.relationship("TestResult", back_populates="question")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    password_changed = db.Column(db.Boolean, default=False, nullable=False)

    # TestResult との関連付け
    results = db.relationship("TestResult", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TestResult(db.Model):
    __tablename__ = "test_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    user_answer_is_correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # User と Question との関連付け
    user = db.relationship("User", back_populates="results")
    question = db.relationship("Question", back_populates="results")

    def __repr__(self):
        return f"<TestResult user_id={self.user_id} q_id={self.question_id} correct={self.user_answer_is_correct}>"
