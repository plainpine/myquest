from database import db

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    choice1 = db.Column(db.String(200))
    choice2 = db.Column(db.String(200))
    choice3 = db.Column(db.String(200))
    choice4 = db.Column(db.String(200))
    correct = db.Column(db.Integer)  # 正解番号（1〜4）
