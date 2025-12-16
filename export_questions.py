import json
import os
from app import app
from database import db
from model import Question

def export_to_json():
    """
    Exports questions from the database to a JSON file.
    The format is compatible with import_questions.py.
    """
    with app.app_context():
        questions = Question.query.order_by(Question.id).all()
        
        output_data = []
        for q in questions:
            output_data.append({
                "question": q.question,
                "choices": [q.choice1, q.choice2, q.choice3, q.choice4],
                "correct": q.correct,
                "category": q.category,
                "explanation": q.explanation,
                "document_url": q.document_url
            })
            
        output_filename = "questions_exported.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"Successfully exported {len(output_data)} questions to {output_filename}")

if __name__ == "__main__":
    export_to_json()
