import os
import io
import threading
import datetime
import json
import logging
import shutil
import random   

import mysql.connector
from flask import Flask, render_template, request, jsonify, send_file, redirect, session

from model import (
    train_model_background,
    extract_embedding_for_image,
    lbp_liveness_check,
    MODEL_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

APP_DIR     = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(APP_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

TRAIN_STATUS_FILE = os.path.join(APP_DIR, "train_status.json")

app = Flask(__name__, static_folder="static", template_folder="templates")
import secrets as _secrets
app.secret_key = _secrets.token_hex(32)   # new key every restart → old sessions invalid

# ---------- MySQL CONFIG ----------
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "root@test",
    "database": "facial_attendance_mini_project",
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ---------- IN-MEMORY MODEL CACHE ----------
# Load once; invalidated when training completes so the new model is picked up.
_model_cache = None

def get_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = _load_model()
    return _model_cache

def _load_model():
    from model import load_model_if_exists
    data = load_model_if_exists()
    if data is None:
        return None
    # Support both old 2-tuple (clf, scaler) and new 3-tuple (clf, scaler, threshold)
    if len(data) == 2:
        clf, scaler = data
        return clf, scaler, 0.70      # default threshold for old models
    return data                        # (clf, scaler, threshold)

def invalidate_model_cache():
    global _model_cache
    _model_cache = None

# ---------- TRAIN STATUS ----------
def write_train_status(d):
    with open(TRAIN_STATUS_FILE, "w") as f:
        json.dump(d, f)

def read_train_status():
    if not os.path.exists(TRAIN_STATUS_FILE):
        return {"running": False, "progress": 0, "message": "Not trained"}
    with open(TRAIN_STATUS_FILE, "r") as f:
        return json.load(f)

write_train_status({"running": False, "progress": 0, "message": "No training yet."})

# ---------- AUTH HELPERS ----------
def current_user():
    u = session.get("user")
    if not isinstance(u, dict):
        session.clear()
        return None
    return u

def require_login(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
    user = cur.fetchone()

    if user:
        name = email
        if user["role"] == "teacher":
            cur.execute("SELECT name FROM teacher WHERE teacher_id=%s", (user["reference_id"],))
            row = cur.fetchone()
            if row: name = row["name"]
        elif user["role"] == "student":
            cur.execute("SELECT name FROM student WHERE student_id=%s", (user["reference_id"],))
            row = cur.fetchone()
            if row: name = row["name"]

        session["user"] = {
            "user_id":      user["user_id"],
            "email":        user["email"],
            "role":         user["role"],
            "reference_id": user["reference_id"],
            "name":         name,
        }
        db.close()
        return redirect("/")

    db.close()
    return render_template("login.html", error="Invalid email or password")

# ---------- SIGNUP ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        db  = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT teacher_id, name FROM teacher ORDER BY name")
        teachers = cur.fetchall()
        db.close()
        return render_template("signup.html", teachers=teachers)

    email        = request.form.get("email", "").strip()
    password     = request.form.get("password", "").strip()
    role         = request.form.get("role", "teacher")
    reference_id = request.form.get("reference_id", "").strip()

    if not email or not password or not reference_id:
        return render_template("signup.html", error="All fields are required.")

    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, password, role, reference_id) VALUES (%s,%s,%s,%s)",
            (email, password, role, reference_id),
        )
        db.commit()
    except mysql.connector.IntegrityError:
        db.close()
        return render_template("signup.html", error="Email already registered.")

    db.close()
    return redirect("/login")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- DASHBOARD ----------
@app.route("/")
@require_login
def index():
    u              = current_user()
    subjects       = []
    recent_records = []

    db  = get_db()
    cur = db.cursor(dictionary=True)

    if u["role"] == "teacher":
        cur.execute("""
            SELECT s.subject_id, s.subject_name, s.semester, s.course
            FROM teacher_subject ts
            JOIN subject s ON ts.subject_id = s.subject_id
            WHERE ts.teacher_id = %s
        """, (u["reference_id"],))
        subjects = cur.fetchall()

        cur.execute("""
            SELECT a.attendance_id, st.name AS student_name,
                   s.subject_name, a.attendance_date, a.attendance_time, a.status
            FROM attendance a
            JOIN student st ON a.student_id = st.student_id
            JOIN subject  s ON a.subject_id  = s.subject_id
            WHERE a.teacher_id = %s
            ORDER BY a.attendance_date DESC, a.attendance_time DESC
            LIMIT 10
        """, (u["reference_id"],))
        recent_records = cur.fetchall()

    db.close()
    return render_template("index.html", user=u, subjects=subjects, recent_records=recent_records)

# ---------- ATTENDANCE STATS ----------
@app.route("/attendance_stats")
@require_login
def attendance_stats():
    u       = current_user()
    db      = get_db()
    cur     = db.cursor(dictionary=True)
    last_30 = [(datetime.date.today() - datetime.timedelta(days=i)) for i in range(29, -1, -1)]

    if u["role"] == "teacher":
        cur.execute("""
            SELECT attendance_date, COUNT(*) as cnt
            FROM attendance
            WHERE teacher_id=%s AND attendance_date >= %s
            GROUP BY attendance_date
        """, (u["reference_id"], last_30[0]))
    else:
        cur.execute("""
            SELECT attendance_date, COUNT(*) as cnt
            FROM attendance
            WHERE attendance_date >= %s
            GROUP BY attendance_date
        """, (last_30[0],))

    rows   = {r["attendance_date"]: r["cnt"] for r in cur.fetchall()}
    db.close()

    counts = [int(rows.get(d, 0)) for d in last_30]
    dates  = [d.strftime("%d-%b") for d in last_30]
    return jsonify({"dates": dates, "counts": counts})

# ---------- ADD STUDENT ----------
@app.route("/add_student", methods=["GET", "POST"])
@require_login
def add_student():
    if request.method == "GET":
        return render_template("add_student.html")

    data   = request.form
    name   = data.get("name", "").strip()
    course = data.get("course", "").strip()
    reg_no = data.get("reg_no", "").strip()
    sem    = data.get("semester", "").strip()

    if not name:
        return jsonify({"error": "name required"}), 400

    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO student (name, course, reg_no, semester, is_active) VALUES (%s,%s,%s,%s,1)",
        (name, course or None, reg_no or None, int(sem) if sem.isdigit() else None),
    )
    sid = cur.lastrowid
    db.commit()
    db.close()

    os.makedirs(os.path.join(DATASET_DIR, str(sid)), exist_ok=True)
    return jsonify({"student_id": sid})

# ---------- UPLOAD FACE ----------
@app.route("/upload_face", methods=["POST"])
@require_login
def upload_face():
    student_id = request.form.get("student_id")
    files      = request.files.getlist("images[]")
    folder     = os.path.join(DATASET_DIR, str(student_id))
    os.makedirs(folder, exist_ok=True)

    saved = 0
    for f in files:
        fname = f"{datetime.datetime.utcnow().timestamp()}_{saved}.jpg"
        f.save(os.path.join(folder, fname))
        saved += 1

    log.info(f"Uploaded {saved} images for student {student_id}")
    return jsonify({"saved": saved})

# ---------- MANAGE STUDENTS ----------
@app.route("/students")
@require_login
def manage_students():
    u   = current_user()
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT student_id, name, course, reg_no, semester, is_active FROM student ORDER BY name")
    raw = cur.fetchall()

    students = []
    for s in raw:
        sid = s["student_id"]

        # Count face images in dataset folder
        folder = os.path.join(DATASET_DIR, str(sid))
        imgs   = []
        if os.path.isdir(folder):
            imgs = [f for f in os.listdir(folder) if f.lower().endswith((".jpg",".jpeg",".png"))]

        # Count attendance records
        cur.execute("SELECT COUNT(*) AS cnt FROM attendance WHERE student_id=%s", (sid,))
        att_count = cur.fetchone()["cnt"]

        students.append({
            "student_id":       sid,
            "name":             s["name"],
            "course":           s["course"],
            "reg_no":           s["reg_no"],
            "semester":         s["semester"],
            "is_active":        bool(s["is_active"]),
            "has_dataset":      len(imgs) > 0,
            "image_count":      len(imgs),
            "attendance_count": att_count,
        })

    db.close()
    return render_template("Manage_students.html", students=students, user=u)

# ---------- DELETE STUDENT ----------
@app.route("/delete_student/<int:student_id>", methods=["POST"])
@require_login
def delete_student(student_id):
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM attendance WHERE student_id=%s", (student_id,))
        cur.execute("DELETE FROM student WHERE student_id=%s",    (student_id,))
        db.commit()
        folder = os.path.join(DATASET_DIR, str(student_id))
        if os.path.exists(folder):
            shutil.rmtree(folder)
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)})
    finally:
        db.close()

# ---------- TRAIN MODEL ----------
@app.route("/train_model")
@require_login
def train_model_route():
    status = read_train_status()
    if status.get("running"):
        return jsonify({"status": "already_running"}), 202

    write_train_status({"running": True, "progress": 0, "message": "Starting training"})

    def _run():
        def update(p, m):
            write_train_status({"running": True, "progress": p, "message": m})
        train_model_background(DATASET_DIR, update)
        write_train_status({"running": False, "progress": 100, "message": "Training complete"})
        invalidate_model_cache()   # force reload of new model on next request
        log.info("Training finished — model cache invalidated")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"status": "started"}), 202

@app.route("/train_status")
def train_status():
    return jsonify(read_train_status())

# ---------- MARK ATTENDANCE PAGE ----------
@app.route("/mark_attendance")
@require_login
def mark_attendance_page():
    u   = current_user()
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT s.subject_id, s.subject_name
        FROM teacher_subject ts
        JOIN subject s ON ts.subject_id = s.subject_id
        WHERE ts.teacher_id = %s
    """, (u["reference_id"],))
    subjects = cur.fetchall()
    db.close()
    return render_template("mark_attendance.html", subjects=subjects, user=u)

# ---------- RECOGNIZE FACE ----------
@app.route("/recognize_face", methods=["POST"])
@require_login
def recognize_face():
    u          = current_user()
    subject_id = request.form.get("subject_id", "").strip()
    img_file   = request.files.get("image")

    if not img_file:
        return jsonify({"recognized": False, "error": "No image received"})
    if not subject_id:
        return jsonify({"recognized": False, "error": "No subject selected"})

    # ── Anti-spoofing: check client-side liveness flag ──────────────────────
    liveness_ok = request.form.get("liveness_confirmed", "false").lower() == "true"
    if not liveness_ok:
        log.info("recognize_face: liveness check not confirmed by client")
        return jsonify({
            "recognized": False,
            "error": "Liveness check failed — please blink or move naturally"
        })

    # ── Read image bytes once (needed for both liveness and embedding) ───────
    image_bytes = img_file.stream.read()

    # ── Anti-spoofing: texture-based liveness check (backend) ────────────────
    # Only run backend liveness if client-side already confirmed liveness.
    # This prevents dim-lighting false rejections on real students.
    if not liveness_ok and not lbp_liveness_check(image_bytes):
        log.info("recognize_face: LBP texture liveness check failed (possible spoof)")
        return jsonify({
            "recognized": False,
            "error": "Liveness check failed — spoof detected"
        })

    # ── Verify teacher is authorized for this subject ────────────────────────
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT id FROM teacher_subject WHERE teacher_id=%s AND subject_id=%s",
        (u["reference_id"], subject_id),
    )
    if not cur.fetchone():
        db.close()
        log.warning(f"Teacher {u['reference_id']} not authorized for subject {subject_id}")
        return jsonify({"recognized": False, "error": "Not authorized for this subject"})

    # ── Extract face embedding ────────────────────────────────────────────────
    import io as _io
    emb = extract_embedding_for_image(_io.BytesIO(image_bytes))
    if emb is None:
        db.close()
        return jsonify({"recognized": False, "error": "No face detected in frame"})

    # ── Load model from cache ─────────────────────────────────────────────────
    model_data = get_model()
    if model_data is None:
        db.close()
        return jsonify({"recognized": False, "error": "Model not trained yet — please train first"})

    clf, scaler, threshold = model_data

    # ── Runtime threshold cap: works without retraining
    threshold = min(threshold, 0.52)
    log.info(f"recognize_face: effective threshold={threshold:.3f}")

    # ── Dimension mismatch guard (old model.pkl vs new feature size) ──────────
    expected_dim = scaler.mean_.shape[0]
    if emb.shape[0] != expected_dim:
        db.close()
        log.error(
            f"Feature dimension mismatch: model expects {expected_dim}-dim "
            f"but got {emb.shape[0]}-dim. Delete model.pkl and retrain."
        )
        return jsonify({
            "recognized": False,
            "error": "⚠️ Model is outdated — please retrain from Dashboard first"
        })

    # ── Predict ───────────────────────────────────────────────────────────────
    emb_scaled            = scaler.transform([emb])[0]
    pred_label, conf      = _predict(clf, emb_scaled)

    log.info(f"recognize_face: label={pred_label}  conf={conf:.3f}  threshold={threshold:.3f}")

    if conf < threshold:
        db.close()
        return jsonify({
            "recognized": False,
            "error": f"Low confidence ({conf:.0%}) — face not recognised"
        })

    # ── Fetch student name ────────────────────────────────────────────────────
    cur.execute("SELECT name FROM student WHERE student_id=%s", (int(pred_label),))
    row  = cur.fetchone()
    name = row["name"] if row else "Unknown"

    now  = datetime.datetime.now()
    date = now.date()
    time = now.strftime("%H:%M:%S")

    # ── Duplicate-attendance guard ────────────────────────────────────────────
    cur.execute(
        "SELECT attendance_id, attendance_time FROM attendance "
        "WHERE student_id=%s AND subject_id=%s AND attendance_date=%s",
        (int(pred_label), subject_id, date),
    )
    existing = cur.fetchone()

    already_marked = existing is not None
    if not already_marked:
        cur.execute(
            "INSERT INTO attendance "
            "(student_id, subject_id, teacher_id, attendance_date, status, attendance_time) "
            "VALUES (%s,%s,%s,%s,'Present',%s)",
            (int(pred_label), subject_id, u["reference_id"], date, time),
        )
        db.commit()
        log.info(f"Attendance marked: {name} (id={pred_label}) for subject {subject_id}")
    else:
        log.info(f"Already marked: {name} at {existing['attendance_time']}")

    db.close()
    return jsonify({
        "recognized":     True,
        "name":           name,
        "student_id":     int(pred_label),
        "confidence":     round(conf, 3),
        "already_marked": already_marked,
        "marked_time":    existing["attendance_time"] if already_marked else time,
    })

def _predict(clf, emb_scaled):
    from model import predict_with_model
    return predict_with_model(clf, emb_scaled)

# ---------- ATTENDANCE RECORDS ----------
@app.route("/attendance_record")
@require_login
def attendance_record():
    u   = current_user()
    db  = get_db()
    cur = db.cursor(dictionary=True)

    if u["role"] == "teacher":
        cur.execute("""
            SELECT a.attendance_id, st.name AS student_name, st.reg_no,
                   s.subject_name, a.attendance_date, a.attendance_time, a.status
            FROM attendance a
            JOIN student st ON a.student_id = st.student_id
            JOIN subject  s ON a.subject_id  = s.subject_id
            WHERE a.teacher_id = %s
            ORDER BY a.attendance_date DESC, a.attendance_time DESC
        """, (u["reference_id"],))
    else:
        cur.execute("""
            SELECT a.attendance_id, st.name AS student_name, st.reg_no,
                   s.subject_name, a.attendance_date, a.attendance_time, a.status
            FROM attendance a
            JOIN student st ON a.student_id = st.student_id
            JOIN subject  s ON a.subject_id  = s.subject_id
            ORDER BY a.attendance_date DESC, a.attendance_time DESC
        """)

    records = cur.fetchall()
    db.close()
    return render_template("attendance_record.html", records=records, user=u)

# ---------- DEBUG DATASET ----------
@app.route("/debug_dataset")
@require_login
def debug_dataset():
    info = {"dataset_dir": DATASET_DIR, "exists": os.path.isdir(DATASET_DIR), "students": []}
    if info["exists"]:
        for sid in os.listdir(DATASET_DIR):
            folder = os.path.join(DATASET_DIR, sid)
            if os.path.isdir(folder):
                imgs = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                info["students"].append({"id": sid, "image_count": len(imgs)})
    info["model_exists"]  = os.path.exists(MODEL_PATH)
    info["train_status"]  = read_train_status()
    info["model_cached"]  = _model_cache is not None
    return jsonify(info)

# ---------- DOWNLOAD CSV ----------
@app.route("/download_csv")
@require_login
def download_csv():
    u   = current_user()
    db  = get_db()
    cur = db.cursor()

    if u["role"] == "teacher":
        cur.execute("""
            SELECT a.attendance_id, st.name, st.reg_no, s.subject_name,
                   a.attendance_date, a.attendance_time, a.status
            FROM attendance a
            JOIN student st ON a.student_id = st.student_id
            JOIN subject  s ON a.subject_id  = s.subject_id
            WHERE a.teacher_id = %s
        """, (u["reference_id"],))
    else:
        cur.execute("""
            SELECT a.attendance_id, st.name, st.reg_no, s.subject_name,
                   a.attendance_date, a.attendance_time, a.status
            FROM attendance a
            JOIN student st ON a.student_id = st.student_id
            JOIN subject  s ON a.subject_id  = s.subject_id
        """)

    rows = cur.fetchall()
    db.close()

    out = io.StringIO()
    out.write("id,student_name,reg_no,subject,date,time,status\n")
    for r in rows:
        out.write(",".join(str(x) for x in r) + "\n")

    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name="attendance.csv")

# ---------- TAB-CLOSE AUTO-LOGOUT ----------
@app.route("/session_end", methods=["GET", "POST"])
def session_end():
    session.clear()
    return "", 204

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        teacher_code = request.form['teacher_code']
        teacher_id = 'T' + str(random.randint(1000, 9999))

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO teacher (teacher_id, TEACHER_CODE, name, email) VALUES (%s, %s, %s, %s)",
            (teacher_id, teacher_code, name, email)
        )
        conn.commit()
        conn.close()
        return redirect('/signup')

    return '''
        <form method="POST">
            Name: <input name="name"><br>
            Email: <input name="email"><br>
            Teacher Code: <input name="teacher_code"><br>
            <button type="submit">Add Teacher</button>
        </form>
    '''
if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)