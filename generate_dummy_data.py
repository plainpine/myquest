import json
from datetime import datetime, timedelta, timezone
import random

from app import app
from database import db
from model import User, Question, TestResult

def generate_dummy_data():
    with app.app_context():
        print("Initializing database and generating dummy data...")
        db.create_all()

        # 1. Ensure Questions exist
        if Question.query.count() == 0:
            print("No questions found, importing from questions.json...")
            try:
                with open("questions.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    q = Question(
                        question=item["question"],
                        choice1=item["choices"][0],
                        choice2=item["choices"][1],
                        choice3=item["choices"][2],
                        choice4=item["choices"][3],
                        correct=item["correct"],
                        category=item.get("category", "none"),
                        explanation=item.get("explanation"),
                        document_url=item.get("document_url")
                    )
                    db.session.add(q)
                db.session.commit()
                print(f"Imported {len(data)} questions.")
            except FileNotFoundError:
                print("questions.json not found. Creating a few default questions.")
                for i in range(1, 11): # Create 10 dummy questions
                    q = Question(
                        question=f"Dummy Question {i}?",
                        choice1="Choice A",
                        choice2="Choice B",
                        choice3="Choice C",
                        choice4="Choice D",
                        correct=random.randint(1, 4),
                        category=f"chapter{random.randint(1, 3)}"
                    )
                    db.session.add(q)
                db.session.commit()
                print(f"Created 10 default questions.")
        else:
            print(f"{Question.query.count()} questions already exist.")

        questions = Question.query.all()
        if not questions:
            print("No questions available to generate test results. Please add questions first.")
            return

        # 2. Create a dummy user
        dummy_email = "dummy@example.com"
        dummy_user = User.query.filter_by(email=dummy_email).first()
        if not dummy_user:
            print(f"Creating dummy user: {dummy_email}")
            dummy_user = User(email=dummy_email, nickname="ダミー生徒")
            dummy_user.set_password("password")
            dummy_user.password_changed = True # No forced change for dummy
            db.session.add(dummy_user)
            db.session.commit()
        else:
            print(f"Dummy user '{dummy_email}' already exists.")

        # 3. Generate TestResult entries
        # Clear existing test results for the dummy user to avoid duplicates if run multiple times
        TestResult.query.filter_by(user_id=dummy_user.id).delete()
        db.session.commit()
        print("Cleared existing test results for dummy user.")

        num_days = 30 # Generate data for the last 30 days
        questions_per_day = 5 # Answer 5 questions per day
        
        start_date = datetime.now(timezone.utc) - timedelta(days=num_days)

        print(f"Generating {num_days * questions_per_day} test results for '{dummy_user.nickname}' over {num_days} days...")
        for i in range(num_days):
            current_date = start_date + timedelta(days=i)
            for _ in range(questions_per_day):
                question = random.choice(questions)
                is_correct = random.choices([True, False], weights=[0.7, 0.3], k=1)[0] # 70% accuracy on average

                # Ensure timestamps are slightly different within the same day for ordering
                timestamp = current_date.replace(
                    hour=random.randint(9, 17),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )

                result = TestResult(
                    user_id=dummy_user.id,
                    question_id=question.id,
                    user_answer_is_correct=is_correct,
                    timestamp=timestamp
                )
                db.session.add(result)
        
        db.session.commit()
        print("Dummy test results generated successfully!")

if __name__ == "__main__":
    generate_dummy_data()
