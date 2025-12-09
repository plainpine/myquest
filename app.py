from flask import Flask, render_template, request, redirect, url_for, session
from database import db
from model import Question
import random   # ランダム出題用

app = Flask(__name__)
app.secret_key = "test123"  # 簡易セッション用（学習用）

# --- DB 設定を追加 ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# --- 起動時にテーブルだけ作成 ---
with app.app_context():
    db.create_all()

# 簡易ユーザー
USERS = {
    "student@example.com": "pass123",
    "admin@example.com": "admin123"
}

# --- ログイン関連 ---
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/try_login", methods=["POST"])
def try_login():
    email = request.form.get("email")
    pw = request.form.get("password")

    if email in USERS and USERS[email] == pw:
        session["user"] = email
        return redirect(url_for("home"))
    else:
        return render_template("login.html", error="ログインに失敗しました")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# --- ホーム ---
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    return render_template("home.html", user=session["user"])

# --- 教材 ---
@app.route("/material")
def material():
    if "user" not in session:
        return redirect("/")
    return render_template("material.html")

# --- 章末テスト ---
@app.route("/section_test", methods=["GET", "POST"])
def section_test():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        answer = int(request.form.get("choice"))
        correct = int(request.form.get("correct"))
        result = (answer == correct)
        return redirect(url_for("result", ok=result))

    # --- DBからランダムに1問取得 ---
    q_list = Question.query.filter_by(category="section").all()
    if not q_list:
        return "章末テスト用の問題がDBにありません"

    q = random.choice(q_list)

    return render_template(
        "section_test.html",
        question=q.question,
        choices=[q.choice1, q.choice2, q.choice3, q.choice4],
        correct=q.correct,   # hidden で送る
    )

# --- 過去問演習 ---
@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        answer = int(request.form.get("choice"))
        correct = int(request.form.get("correct"))
        result = (answer == correct)
        return redirect(url_for("result", ok=result))

    q_list = Question.query.filter_by(category="practice").all()
    if not q_list:
        return "過去問の問題がDBにありません"

    q = random.choice(q_list)

    return render_template(
        "practice.html",
        question=q.question,
        choices=[q.choice1, q.choice2, q.choice3, q.choice4],
        correct=q.correct,
    )

# --- 結果画面 ---
@app.route("/result")
def result():
    if "user" not in session:
        return redirect("/")
    ok = request.args.get("ok") == "True"
    return render_template("result.html", ok=ok)

# --- 管理者画面 ---
@app.route("/admin")
def admin():
    if session.get("user") != "admin@example.com":
        return redirect("/")
    return render_template("admin.html")

# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
