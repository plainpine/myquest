import json
from model import Question
from app import app
from database import db 

# JSON → DB インポート
def import_json(json_file):
    print(f"JSON 読み込み中: {json_file}")
    with app.app_context():

        db.create_all()

        with open(json_file, "r", encoding="utf-8") as f:
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

        print("インポート完了！")

# メイン処理
if __name__ == "__main__":
    import_json("questions.json")
