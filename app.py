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

    # "category"が数字であるものを章カテゴリとして取得
    all_categories_tuples = db.session.query(Question.category).distinct().all()
    all_categories = [c[0] for c in all_categories_tuples if c[0] is not None]
    
    # isdigit()で数字のみを抽出し、数値としてソート
    section_categories = sorted([c for c in all_categories if c.isdigit()], key=int)

    # 表示用の章名をマッピングする辞書 (キーは文字列の数字)
    section_display_names = {
        "1": "第1章",
        "2": "第2章",
        "3": "第3章",
        "4": "第4章",
        "5": "第5章",
        "6": "第6章",
        # 必要に応じて章と表示名をここに追加
    }

    return render_template(
        "home.html",
        user=session["user"],
        section_categories=section_categories,
        section_display_names=section_display_names
    )

# --- 教材 ---
@app.route("/material")
def material():
    if "user" not in session:
        return redirect("/")
    return render_template("material.html")

# --- 章末テスト ---
@app.route("/section_test/<string:section_category>", methods=["GET", "POST"])
def section_test(section_category):
    if "user" not in session:
        return redirect("/")

    section_display_names = {
        "1": "第1章",
        "2": "第2章",
        "3": "第3章",
        "4": "第4章",
        "5": "第5章",
        "6": "第6章",
    }
    display_name = section_display_names.get(section_category, f"章 {section_category}")

    if request.method == "POST":
        questions = Question.query.filter_by(category=section_category).all()
        results = []
        correct_count = 0
        for q in questions:
            choice_id = f"choice_{q.id}"
            user_answer = request.form.get(choice_id)
            
            # ユーザーが回答しなかった場合
            if user_answer is None:
                is_correct = False
                user_answer_text = "未回答"
            else:
                user_answer = int(user_answer)
                is_correct = (user_answer == q.correct)
                if is_correct:
                    correct_count += 1
                # ユーザーの回答番号に対応するテキストを取得
                user_answer_text = getattr(q, f"choice{user_answer}", "無効な選択")

            # 正解の選択肢テキストを取得
            correct_answer_text = getattr(q, f"choice{q.correct}", "正解不明")

            results.append({
                "question": q.question,
                "user_answer": user_answer_text,
                "correct_answer": correct_answer_text,
                "is_correct": is_correct
            })
        
        total_questions = len(questions)

        return render_template(
            "result.html",
            results=results,
            correct_count=correct_count,
            total_questions=total_questions,
            display_name=display_name
        )

    questions = Question.query.filter_by(category=section_category).all()
    if not questions:
        return f"{display_name}用の問題がDBにありません"

    return render_template(
        "section_test.html",
        questions=questions,
        display_name=display_name
    )

# --- 過去問演習 ---
@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        choice = request.form.get("choice")
        if choice is None:
            return redirect(url_for("result", ok=False))
        answer = int(choice)
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
