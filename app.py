from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import db
from model import Question, User, TestResult
import random   # ランダム出題用
from itertools import groupby

from functools import wraps

app = Flask(__name__)
app.secret_key = "test123"  # 簡易セッション用（学習用）

# --- DB 設定を追加 ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# --- 起動時にテーブルだけ作成 ---
with app.app_context():
    db.create_all()

# --- ログインユーザーをコンテキストプロセッサでテンプレートに渡す ---
@app.context_processor
def inject_user():
    if 'user' in session:
        user = User.query.filter_by(email=session['user']).first()
        return dict(current_user=user)
    return dict(current_user=None)

# --- ログイン必須デコレーター ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash('ログインが必要です', 'warning')
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# --- 管理者用デコレーター ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user") != "admin@example.com":
            flash('管理者権限が必要です', 'danger')
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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
    flash('ログアウトしました。', 'info')
    return redirect("/")

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
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
            flash('パスワードが変更されました。', 'success')
            return redirect(url_for("home"))
        else:
            # This case should not happen if login_required works
            return redirect(url_for("login", error="ユーザーが見つかりません"))

    return render_template("change_password.html")

# --- ホーム ---
@app.route("/home")
@login_required
def home():
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

# --- プロフィール管理 ---
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.filter_by(email=session['user']).first()
    if not user:
        # Should not happen with @login_required
        return redirect(url_for('login'))

    if request.method == "POST":
        nickname = request.form.get("nickname")
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        changes_made = False

        # 1. パスワード変更の検証と処理
        if current_password or new_password or confirm_new_password:
            if not user.check_password(current_password):
                flash('現在のパスワードが正しくありません。', 'danger')
                return redirect(url_for('profile'))
            if new_password != confirm_new_password:
                flash('新しいパスワードが一致しません。', 'danger')
                return redirect(url_for('profile'))
            if not new_password:
                flash('新しいパスワードを入力してください。', 'danger')
                return redirect(url_for('profile'))
            
            user.set_password(new_password)
            changes_made = True

        # 2. ニックネームの更新
        # Note: nickname can be None, so handle comparison carefully
        if (user.nickname or "") != (nickname or ""):
            user.nickname = nickname
            changes_made = True

        # 3. 変更があればコミットと通知
        if changes_made:
            db.session.commit()
            flash('プロフィールが更新されました。', 'success')
        else:
            flash('変更内容がありませんでした。', 'info')

        return redirect(url_for('home'))

    return render_template("profile.html")


# --- 教材 ---
@app.route("/material")
@login_required
def material():
    return render_template("material.html")

# --- 章末テスト ---
@app.route("/section_test/<string:section_category>", methods=["GET", "POST"])
@login_required
def section_test(section_category):
    display_name = f"第{section_category}章"

    if request.method == "POST":
        user = User.query.filter_by(email=session["user"]).first()
        if not user:
            # Should not happen due to @login_required
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
@login_required
def practice():
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
@login_required
def retest():
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
@login_required
def result():
    ok = request.args.get("ok") == "True"
    return render_template("result.html", ok=ok)

# --- 管理者画面 ---
@app.route("/admin")
@admin_required
def admin_home():
    return redirect(url_for("admin_questions"))

@app.route("/admin/questions")
@admin_required
def admin_questions():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    
    # "category"が数字であるものを章カテゴリとして取得
    all_categories_tuples = db.session.query(Question.category).distinct().all()
    all_categories = [c[0] for c in all_categories_tuples if c[0] is not None]
    
    # isdigit()で数字のみを抽出し、数値としてソート
    section_categories = sorted([c for c in all_categories if c.isdigit()], key=int)

    query = Question.query.order_by(Question.id)
    if category:
        query = query.filter_by(category=category)
    
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    questions = pagination.items
        
    return render_template("admin.html", 
                           questions=questions, 
                           section_categories=section_categories,
                           selected_category=category,
                           pagination=pagination)

@app.route("/admin/question/add", methods=["GET", "POST"])
@admin_required
def add_question():
    if request.method == "POST":
        new_question = Question(
            question=request.form["question"],
            choice1=request.form["choice1"],
            choice2=request.form["choice2"],
            choice3=request.form["choice3"],
            choice4=request.form["choice4"],
            correct=int(request.form["correct"]),
            category=request.form["category"],
            explanation=request.form["explanation"],
            document_url=request.form["document_url"]
        )
        db.session.add(new_question)
        db.session.commit()
        return redirect(url_for("admin_questions"))
    return render_template("question_form.html", question=None)

@app.route("/admin/question/edit/<int:question_id>", methods=["GET", "POST"])
@admin_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    if request.method == "POST":
        question.question = request.form["question"]
        question.choice1 = request.form["choice1"]
        question.choice2 = request.form["choice2"]
        question.choice3 = request.form["choice3"]
        question.choice4 = request.form["choice4"]
        question.correct = int(request.form["correct"])
        question.category = request.form["category"]
        question.explanation = request.form["explanation"]
        question.document_url = request.form["document_url"]
        db.session.commit()
        return redirect(url_for("admin_questions"))
    return render_template("question_form.html", question=question)

@app.route("/admin/question/delete/<int:question_id>", methods=["POST"])
@admin_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for("admin_questions"))

@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.filter(User.email != 'admin@example.com').order_by(User.id).all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/user/add", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template("user_form.html", error="このメールアドレスは既に使用されています。")

        new_user = User(email=email)
        new_user.set_password(password)
        new_user.password_changed = False # Force password change on first login
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("admin_users"))
    return render_template("user_form.html")

@app.route("/admin/user/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.email == 'admin@example.com':
        # Prevent admin from being deleted
        return redirect(url_for("admin_users"))
    
    # Also delete related test results
    TestResult.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin_users"))

@app.route("/admin/user/change_password/<int:user_id>", methods=["GET", "POST"])
@admin_required
def admin_change_password(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            return render_template("user_change_password.html", user=user, error="パスワードが一致しません")

        user.set_password(new_password)
        user.password_changed = False # Force password change on next login
        db.session.commit()
        return redirect(url_for("admin_users"))
        
    return render_template("user_change_password.html", user=user)


# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
