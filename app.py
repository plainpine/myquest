from flask import Flask, render_template, request, redirect, url_for, session
from database import db
from model import Question

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

# --- 章末テスト（固定問題1問） ---
@app.route("/section_test", methods=["GET", "POST"])
def section_test():
    if "user" not in session:
        return redirect("/")

    question = "Python でリストを作る構文として正しいものはどれ？"
    choices = ["(1) {1,2,3}", "(2) [1,2,3]", "(3) <1,2,3>", "(4) (1,2,3)"]
    correct = 2  # [1,2,3]

    if request.method == "POST":
        answer = int(request.form.get("choice"))
        result = (answer == correct)
        return redirect(url_for("result", ok=result))

    return render_template("section_test.html", question=question, choices=choices)

# --- 過去問演習（固定1問） ---
@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "user" not in session:
        return redirect("/")

    question = "PEP8 が定めているのは何？"
    choices = ["(1) Python の標準入力方法",
               "(2) Python のコーディング規約",
               "(3) Python の実行速度規約",
               "(4) Python のセキュリティ規約"]
    correct = 2

    if request.method == "POST":
        answer = int(request.form.get("choice"))
        result = (answer == correct)
        return redirect(url_for("result", ok=result))

    return render_template("practice.html", question=question, choices=choices)

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
