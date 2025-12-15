from flask import Flask, render_template, request, redirect, url_for, session
from database import db
from model import Question, User, TestResult
import random   # ランダム出題用
from itertools import groupby

app = Flask(__name__)
app.secret_key = "test123"  # 簡易セッション用（学習用）

# --- DB 設定を追加 ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# --- 起動時にテーブルだけ作成 ---
with app.app_context():
    db.create_all()

# --- ログイン関連 ---
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/try_login", methods=["POST"])
def try_login():
    email = request.form.get("email")
    pw = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(pw):
        session["user"] = user.email
        if not user.password_changed:
            return redirect(url_for("change_password"))
        return redirect(url_for("home"))
    else:
        return render_template("login.html", error="ログインに失敗しました")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            return render_template("change_password.html", error="パスワードが一致しません")

        user = User.query.filter_by(email=session["user"]).first()
        if user:
            user.set_password(new_password)
            user.password_changed = True
            db.session.commit()
            return redirect(url_for("home"))
        else:
            return redirect(url_for("login", error="ユーザーが見つかりません"))

    return render_template("change_password.html")

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

    return render_template(
        "home.html",
        user=session["user"],
        section_categories=section_categories
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

    display_name = f"第{section_category}章"

    if request.method == "POST":
        user = User.query.filter_by(email=session["user"]).first()
        if not user:
            return redirect(url_for("login", error="ユーザーが見つかりません"))

        # セッションから問題IDリストを取得
        question_ids = session.get(f"section_test_{section_category}_questions", [])
        if not question_ids:
            return redirect(url_for("home")) # セッションが切れた場合

        questions = Question.query.filter(Question.id.in_(question_ids)).all()
        # 画面表示の順序を保つためにIDをキーにした辞書を作成
        questions_dict = {q.id: q for q in questions}
        # セッションに保存されたIDの順序で問題リストを再構築
        ordered_questions = [questions_dict[id] for id in question_ids if id in questions_dict]

        results = []
        correct_count = 0
        for q in ordered_questions:
            choice_id = f"choice_{q.id}"
            user_answer = request.form.get(choice_id)
            
            if user_answer is None:
                is_correct = False
                user_answer_text = "未回答"
            else:
                user_answer = int(user_answer)
                is_correct = (user_answer == q.correct)
                if is_correct:
                    correct_count += 1
                user_answer_text = getattr(q, f"choice{user_answer}", "無効な選択")

            # 結果をDBに保存
            new_result = TestResult(
                user_id=user.id,
                question_id=q.id,
                user_answer_is_correct=is_correct
            )
            db.session.add(new_result)

            correct_answer_text = getattr(q, f"choice{q.correct}", "正解不明")

            results.append({
                "question": q.question,
                "user_answer": user_answer_text,
                "correct_answer": correct_answer_text,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "document_url": q.document_url
            })
        
        db.session.commit()
        total_questions = len(ordered_questions)

        return render_template(
            "result.html",
            results=results,
            correct_count=correct_count,
            total_questions=total_questions,
            display_name=display_name
        )

    # GET request
    num_questions_str = request.args.get("num_questions", "10")
    try:
        num_questions = int(num_questions_str)
    except ValueError:
        num_questions = 10

    all_section_questions = Question.query.filter_by(category=section_category).all()
    if not all_section_questions:
        return f"{display_name}用の問題がDBにありません"

    num_to_select = min(len(all_section_questions), num_questions)
    selected_questions = random.sample(all_section_questions, num_to_select)

    # 選んだ問題のIDをセッションに保存
    session[f"section_test_{section_category}_questions"] = [q.id for q in selected_questions]

    return render_template(
        "section_test.html",
        questions=selected_questions,
        display_name=display_name,
        section_category=section_category
    )

# --- 模擬試験 ---
@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "user" not in session:
        return redirect("/")

    display_name = "模擬試験"

    if request.method == "POST":
        user = User.query.filter_by(email=session["user"]).first()
        if not user:
            return redirect(url_for("login", error="ユーザーが見つかりません"))

        # セッションから問題IDリストを取得
        question_ids = session.get("practice_questions", [])
        if not question_ids:
            return redirect(url_for("home")) #セッションが切れた場合

        questions = Question.query.filter(Question.id.in_(question_ids)).all()
        
        # 画面表示の順序を保つためにIDをキーにした辞書を作成
        questions_dict = {q.id: q for q in questions}
        # セッションに保存されたIDの順序で問題リストを再構築
        ordered_questions = [questions_dict[id] for id in question_ids if id in questions_dict]

        results = []
        correct_count = 0
        for q in ordered_questions:
            choice_id = f"choice_{q.id}"
            user_answer = request.form.get(choice_id)
            
            if user_answer is None:
                is_correct = False
                user_answer_text = "未回答"
            else:
                user_answer = int(user_answer)
                is_correct = (user_answer == q.correct)
                if is_correct:
                    correct_count += 1
                user_answer_text = getattr(q, f"choice{user_answer}", "無効な選択")

            # 結果をDBに保存
            new_result = TestResult(
                user_id=user.id,
                question_id=q.id,
                user_answer_is_correct=is_correct
            )
            db.session.add(new_result)

            correct_answer_text = getattr(q, f"choice{q.correct}", "正解不明")

            results.append({
                "question": q.question,
                "user_answer": user_answer_text,
                "correct_answer": correct_answer_text,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "document_url": q.document_url
            })
        
        db.session.commit()
        total_questions = len(ordered_questions)

        # 結果をresult.htmlに渡す
        return render_template(
            "result.html",
            results=results,
            correct_count=correct_count,
            total_questions=total_questions,
            display_name=display_name
        )

    # GET request
    num_questions_str = request.args.get("num_questions", "10")
    try:
        num_questions = int(num_questions_str)
    except ValueError:
        num_questions = 10

    all_questions = Question.query.all()
    if not all_questions:
        return "問題がDBにありません"

    num_to_select = min(len(all_questions), num_questions)
    selected_questions = random.sample(all_questions, num_to_select)
    
    # 選んだ問題のIDをセッションに保存
    session["practice_questions"] = [q.id for q in selected_questions]

    return render_template(
        "practice.html",
        questions=selected_questions,
        display_name=display_name
    )


# --- 再テスト ---
@app.route("/retest", methods=["GET", "POST"])
def retest():
    if "user" not in session:
        return redirect("/")

    user = User.query.filter_by(email=session["user"]).first()
    if not user:
        return redirect(url_for("login", error="ユーザーが見つかりません"))

    display_name = "苦手問題の再テスト"

    if request.method == "POST":
        question_ids = session.get("retest_questions", [])
        if not question_ids:
            return redirect(url_for("home"))

        questions = Question.query.filter(Question.id.in_(question_ids)).all()
        questions_dict = {q.id: q for q in questions}
        ordered_questions = [questions_dict[id] for id in question_ids if id in questions_dict]

        results = []
        correct_count = 0
        for q in ordered_questions:
            choice_id = f"choice_{q.id}"
            user_answer = request.form.get(choice_id)
            
            if user_answer is None:
                is_correct = False
                user_answer_text = "未回答"
            else:
                user_answer = int(user_answer)
                is_correct = (user_answer == q.correct)
                if is_correct:
                    correct_count += 1
                user_answer_text = getattr(q, f"choice{user_answer}", "無効な選択")

            # Update existing result or create new one
            # For simplicity, we just add a new result every time.
            new_result = TestResult(
                user_id=user.id,
                question_id=q.id,
                user_answer_is_correct=is_correct
            )
            db.session.add(new_result)

            correct_answer_text = getattr(q, f"choice{q.correct}", "正解不明")

            results.append({
                "question": q.question,
                "user_answer": user_answer_text,
                "correct_answer": correct_answer_text,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "document_url": q.document_url
            })
        
        db.session.commit()
        total_questions = len(ordered_questions)

        return render_template(
            "result.html",
            results=results,
            correct_count=correct_count,
            total_questions=total_questions,
            display_name=display_name
        )

    # GET request: 苦手問題を取得
    eligible_question_ids = []
    
    # ユーザーの全テスト結果を問題IDと時間でソートして取得
    user_results = TestResult.query.filter_by(user_id=user.id).order_by(
        TestResult.question_id, TestResult.timestamp.desc()
    ).all()

    # 問題IDごとに結果をグループ化
    for q_id, results_group in groupby(user_results, key=lambda r: r.question_id):
        results_list = list(results_group)
        
        # 直近3回の結果を取得
        latest_three = results_list[:3]
        
        # 3回連続で正解しているかチェック
        is_mastered = False
        if len(latest_three) == 3:
            if all(r.user_answer_is_correct for r in latest_three):
                is_mastered = True
        
        # マスターしていなければ、再テスト候補に追加
        if not is_mastered:
            eligible_question_ids.append(q_id)

    if not eligible_question_ids:
        return render_template("retest.html", questions=[], display_name=display_name)
    
    # 苦手問題から出題
    retest_questions = Question.query.filter(Question.id.in_(eligible_question_ids)).all()
    
    num_questions_str = request.args.get("num_questions", "10")
    try:
        num_questions = int(num_questions_str)
    except ValueError:
        num_questions = 10

    num_to_select = min(len(retest_questions), num_questions)
    selected_questions = random.sample(retest_questions, num_to_select)
    
    session["retest_questions"] = [q.id for q in selected_questions]

    return render_template(
        "retest.html",
        questions=selected_questions,
        display_name=display_name
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
