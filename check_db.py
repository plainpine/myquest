# check_db.py
from app import app
from database import db
from model import Question, User

def read_all_questions():
    with app.app_context():

        # テーブルが無い場合はエラー防止（存在しなければ作成）
        db.create_all()

        questions = Question.query.all()

        print("=== questions テーブルの内容 ===")

        if not questions:
            print("(データなし)")
            return

        for q in questions:
            print(f"[ID] {q.id}")
            print(f"  問題   : {q.question}")
            print(f"  選択肢1: {q.choice1}")
            print(f"  選択肢2: {q.choice2}")
            print(f"  選択肢3: {q.choice3}")
            print(f"  選択肢4: {q.choice4}")
            print(f"  正解   : {q.correct}")
            print(f"  区分   : {q.category}")
            print(f"  解説   : {q.explanation}")
            print(f"  URL    : {q.document_url}")
            print("-" * 40)

def create_initial_user():
    with app.app_context():
        db.create_all()
        # Check if user already exists
        user = User.query.filter_by(email="student@example.com").first()
        if not user:
            new_user = User(email="student@example.com")
            new_user.set_password("pass123")
            db.session.add(new_user)
            db.session.commit()
            print("Initial user created.")
        else:
            print("Initial user already exists.")
        
        # Add admin user if it does not exist
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            new_admin = User(email="admin@example.com")
            new_admin.set_password("admin123")
            new_admin.password_changed = True  # Admin user does not need to change password
            db.session.add(new_admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    create_initial_user()
    read_all_questions()