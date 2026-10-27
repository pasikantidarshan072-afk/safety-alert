import os, json, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory
from werkzeug.utils import secure_filename
import requests

APP_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
DB_PATH = os.path.join(APP_DIR, "safety_alerts.db")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Demo credentials. Set ADMIN_USERNAME and ADMIN_PASSWORD environment variables before deployment.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_type TEXT NOT NULL,
            person_name TEXT NOT NULL,
            age TEXT,
            description TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            last_seen_location TEXT NOT NULL,
            contact TEXT NOT NULL,
            photo_filename TEXT,
            status TEXT NOT NULL DEFAULT 'Pending review',
            public_approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            location TEXT,
            contact TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        )""")

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_now():
    return {"current_year": datetime.now().year}

@app.route("/")
def index():
    with db() as con:
        cases = con.execute("""
            SELECT * FROM cases WHERE public_approved=1 AND status='Active'
            ORDER BY created_at DESC
        """).fetchall()
    return render_template("index.html", cases=cases)

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        person_type = request.form.get("person_type", "Missing child")
        if person_type not in ("Missing child", "Wanted person / public safety alert"):
            person_type = "Missing child"
        name = request.form.get("person_name", "").strip()
        description = request.form.get("description", "").strip()
        last_seen = request.form.get("last_seen", "").strip()
        location = request.form.get("last_seen_location", "").strip()
        contact = request.form.get("contact", "").strip()
        age = request.form.get("age", "").strip()
        photo = request.files.get("photo")
        if not all([name, description, last_seen, location, contact]):
            flash("Please fill in all required fields.", "error")
            return render_template("report.html")
        filename = None
        if photo and photo.filename:
            if not allowed_file(photo.filename):
                flash("Photo must be JPG, PNG, or WEBP.", "error")
                return render_template("report.html")
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{photo.filename}")
            photo.save(os.path.join(UPLOAD_DIR, filename))
        with db() as con:
            con.execute("""
              INSERT INTO cases(person_type, person_name, age, description, last_seen,
                last_seen_location, contact, photo_filename, status, public_approved, created_at)
              VALUES(?,?,?,?,?,?,?,?, 'Pending review', 0, ?)
            """, (person_type, name, age, description, last_seen, location, contact,
                  filename, datetime.now().isoformat(timespec="seconds")))
        flash("Report submitted for review. It will not appear publicly until an authorized reviewer approves it.", "success")
        return redirect(url_for("report"))
    return render_template("report.html")

@app.route("/case/<int:case_id>", methods=["GET", "POST"])
def case_detail(case_id):
    with db() as con:
        case = con.execute("SELECT * FROM cases WHERE id=? AND public_approved=1 AND status='Active'", (case_id,)).fetchone()
        if not case:
            abort(404)
        if request.method == "POST":
            message = request.form.get("message", "").strip()
            location = request.form.get("location", "").strip()
            contact = request.form.get("contact", "").strip()
            if not message:
                flash("Please enter the information you want to share.", "error")
            else:
                con.execute("INSERT INTO tips(case_id,message,location,contact,created_at) VALUES(?,?,?,?,?)",
                            (case_id, message, location, contact, datetime.now().isoformat(timespec="seconds")))
                flash("Tip sent to the reviewing team. If this is an emergency, contact local emergency services directly.", "success")
                return redirect(url_for("case_detail", case_id=case_id))
    return render_template("case.html", case=case)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Only approved public active cases can serve a photo.
    with db() as con:
        row = con.execute("SELECT id FROM cases WHERE photo_filename=? AND public_approved=1 AND status='Active'", (filename,)).fetchone()
    if not row:
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect login.", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as con:
        cases = con.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        tips = con.execute("""
            SELECT tips.*, cases.person_name FROM tips JOIN cases ON tips.case_id=cases.id
            ORDER BY tips.created_at DESC
        """).fetchall()
    return render_template("admin.html", cases=cases, tips=tips)

@app.route("/admin/case/<int:case_id>/update", methods=["POST"])
@admin_required
def update_case(case_id):
    status = request.form.get("status", "Pending review")
    if status not in ("Pending review", "Active", "Resolved", "Closed"):
        abort(400)
    approved = 1 if request.form.get("public_approved") == "on" else 0
    with db() as con:
        con.execute("UPDATE cases SET status=?, public_approved=? WHERE id=?", (status, approved, case_id))
    flash("Case updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/case/<int:case_id>/summary", methods=["POST"])
@admin_required
def ai_summary(case_id):
    with db() as con:
        case = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        abort(404)
    prompt = (
        "You assist an authorized safety-alert reviewer. Summarize the report below into concise, neutral "
        "review notes. Do not infer guilt, identity, or a person's location beyond the supplied text. "
        "Flag missing information and remind the reviewer to verify facts before publication. "
        "Do not make decisions or publish anything automatically.\\n\\n"
        f"Type: {case['person_type']}\\nName: {case['person_name']}\\nAge: {case['age']}\\n"
        f"Description: {case['description']}\\nLast seen time: {case['last_seen']}\\n"
        f"Reported location: {case['last_seen_location']}"
    )
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    try:
        response = requests.post("http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False}, timeout=45)
        response.raise_for_status()
        result = response.json().get("response", "Ollama returned no summary.")
    except Exception as exc:
        result = f"Ollama is unavailable. Start Ollama and pull the configured model. Details: {exc}"
    return render_template("ai_summary.html", case=case, result=result)

@app.errorhandler(413)
def too_large(_):
    return "Upload too large. Maximum file size is 5 MB.", 413

init_db()
if __name__ == "__main__":
    app.run(debug=True)
