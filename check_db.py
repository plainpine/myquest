# check_db.py
from app import app
from database import db
from model import Question

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
            print("-" * 40)

if __name__ == "__main__":
    read_all_questions()