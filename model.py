import os
import cv2
import numpy as np
import pickle
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler

MODEL_PATH = "model.pkl"

# ── Lighting quality gate ─────────────────────────────────────────────────────
# Frames darker than this (0–255 mean brightness) are rejected at recognition
# time with "improve lighting" instead of attempting unreliable recognition.
# 80 ≈ a dimly-lit room; daylight/indoor-lit frames are typically 100–180.
LIGHTING_MIN_MEAN = 80

# ── Cascades ──────────────────────────────────────────────────────────────────
_CASCADE_PATH  = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_PROFILE_PATH  = cv2.data.haarcascades + "haarcascade_profileface.xml"
_cascade       = cv2.CascadeClassifier(_CASCADE_PATH)
_cascade_prof  = cv2.CascadeClassifier(_PROFILE_PATH)

if _cascade.empty():
    raise RuntimeError("Haarcascade XML not found. Run: pip install --upgrade opencv-python")


# ══════════════════════════════════════════════════════════════════════════════
#  LIGHTING NORMALISATION  (the core fix for proxy attendance)
# ══════════════════════════════════════════════════════════════════════════════
def _normalise_lighting(gray_face):
    """
    Four-stage lighting normalisation — tuned for dark/dim webcam conditions.

    Stage 0 – Brightness rescue
        If the face region is very dark (mean < 60), linearly stretch the pixel
        range BEFORE CLAHE so subsequent stages have enough signal to work with.
        This directly fixes the dark-room webcam recognition failure.

    Stage 1 – CLAHE
        Aggressive clip-limit (4.0) and fine 6x6 grid for dark frames.

    Stage 2 – Adaptive gamma
        Dark face  (mean < 80)  -> gamma = 0.45  (very strong brightening)
        Dim face   (mean < 120) -> gamma = 0.60  (moderate brightening)
        Normal                  -> gamma = 0.75  (slight brightening)

    Stage 3 – Gaussian high-pass
        Removes residual low-frequency illumination gradients.
    """
    mean_val = float(np.mean(gray_face))

    # Stage 0: pre-boost very dark faces
    if mean_val < 60:
        mn, mx = float(gray_face.min()), float(gray_face.max())
        if mx > mn:
            gray_face = np.clip(
                (gray_face.astype(np.float32) - mn) / (mx - mn) * 180 + 40,
                0, 255
            ).astype(np.uint8)

    # Stage 1: CLAHE — more aggressive for dark frames
    clip   = 4.0 if mean_val < 100 else 3.0
    grid   = (6, 6) if mean_val < 100 else (4, 4)
    clahe  = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
    stage1 = clahe.apply(gray_face)

    # Stage 2: adaptive gamma
    if mean_val < 80:
        gamma = 0.45
    elif mean_val < 120:
        gamma = 0.60
    else:
        gamma = 0.75
    lut    = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)],
                      dtype=np.uint8)
    stage2 = cv2.LUT(stage1, lut)

    # Stage 3: high-pass to remove illumination gradients
    blur   = cv2.GaussianBlur(stage2, (15, 15), 0)
    hp     = cv2.addWeighted(stage2, 1.5, blur, -0.5, 128)
    stage3 = np.clip(hp, 0, 255).astype(np.uint8)

    return stage3


# ══════════════════════════════════════════════════════════════════════════════
#  FACE DETECTION  (frontal + profile, keeps larger detection)
# ══════════════════════════════════════════════════════════════════════════════
def _detect_and_crop_face(gray_frame):
    """
    Try frontal cascade first, then profile.  Returns a lighting-normalised
    80×80 face crop, or None if nothing found.

    80×80 (up from 64×64) gives more LBP cells and improves accuracy slightly.
    """
    best = None

    for cascade, scale, neigh in [
        (_cascade,      1.05, 6),   # frontal  – strict
        (_cascade,      1.10, 4),   # frontal  – relaxed
        (_cascade_prof, 1.10, 5),   # profile
    ]:
        faces = cascade.detectMultiScale(
            gray_frame,
            scaleFactor=scale,
            minNeighbors=neigh,
            minSize=(50, 50),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        if len(faces) > 0:
            candidate = max(faces, key=lambda r: r[2] * r[3])
            if best is None or candidate[2] * candidate[3] > best[2] * best[3]:
                best = candidate
            break   # frontal found — no need for profile

    if best is None:
        return None

    x, y, w, h = best
    pad = int(0.12 * max(w, h))
    x1  = max(0, x - pad)
    y1  = max(0, y - pad)
    x2  = min(gray_frame.shape[1], x + w + pad)
    y2  = min(gray_frame.shape[0], y + h + pad)

    crop = gray_frame[y1:y2, x1:x2]
    face = cv2.resize(crop, (80, 80))
    return _normalise_lighting(face)   # ← lighting fix applied here


# ══════════════════════════════════════════════════════════════════════════════
#  LBP FEATURE EXTRACTION  (5×5 grid, 288 → 450-dim)
# ══════════════════════════════════════════════════════════════════════════════
def _compute_lbp(face_80):
    """
    Spatial LBP histogram over a 5×5 grid of 16×16-pixel cells.
    Output: 450-dimensional float32 vector  (5×5 cells × 18 bins).

    A finer grid captures more spatial structure while staying fast.
    """
    try:
        from skimage.feature import local_binary_pattern
        lbp = local_binary_pattern(face_80, P=16, R=2, method="uniform")
    except ImportError:
        lbp = _manual_lbp(face_80)

    n_bins   = 18   # uniform LBP with P=16 → 18 patterns
    cell_sz  = 16   # 80 / 5 = 16
    hist_all = []

    for r in range(5):
        for c in range(5):
            patch = lbp[r * cell_sz:(r + 1) * cell_sz,
                        c * cell_sz:(c + 1) * cell_sz]
            h, _  = np.histogram(patch, bins=n_bins, range=(0, n_bins))
            total = h.sum()
            h     = (h.astype(np.float32) / total) if total > 0 \
                    else np.zeros(n_bins, dtype=np.float32)
            hist_all.extend(h)

    vec = np.array(hist_all, dtype=np.float32)   # 450-dim
    return np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)


def _manual_lbp(gray):
    """Pure-numpy 8-neighbour LBP fallback."""
    lbp     = np.zeros_like(gray, dtype=np.uint8)
    offsets = [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]
    for bit, (dy, dx) in enumerate(offsets):
        shifted = np.roll(np.roll(gray, dy, axis=0), dx, axis=1)
        lbp    |= ((gray >= shifted).astype(np.uint8) << bit)
    return lbp.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
def load_model_if_exists():
    """Return (clf, scaler, threshold) tuple or None."""
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_with_model(clf, emb):
    """Return (predicted_label, confidence_probability)."""
    probs = clf.predict_proba([emb])[0]
    idx   = int(np.argmax(probs))
    return clf.classes_[idx], float(probs[idx])


def extract_embedding_for_image(file_stream, check_lighting=False):
    """
    Read a JPEG/PNG from file_stream, detect face, extract LBP features.
    Returns a 450-dim float32 vector, or None if no face found.

    check_lighting=True  → used during RECOGNITION: rejects frames where the
    mean pixel brightness is below LIGHTING_MIN_MEAN (too dark to be reliable).
    check_lighting=False → used during TRAINING: lighting normalisation still
    applied so the model learns from good captures.
    """
    file_bytes = np.frombuffer(file_stream.read(), np.uint8)
    img        = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Lighting gate (recognition only) ─────────────────────────────────────
    # Reject frames that are too dark to recognise reliably.
    # Threshold: mean brightness < 80 (0-255 scale) → poor lighting.
    if check_lighting:
        frame_mean = float(np.mean(gray))
        if frame_mean < LIGHTING_MIN_MEAN:
            return "DARK"   # sentinel — caller shows "improve lighting" message

    face_80 = _detect_and_crop_face(gray)
    if face_80 is None:
        return None

    emb = _compute_lbp(face_80)
    return emb if np.isfinite(emb).all() else None


# ══════════════════════════════════════════════════════════════════════════════
#  LIVENESS CHECK  (anti-proxy / anti-photo spoofing)
# ══════════════════════════════════════════════════════════════════════════════
def lbp_liveness_check(image_bytes):
    """
    Multi-cue liveness detection to reject photo / screen spoofs.

    Cue 1 – LBP texture variance
        Printed photos and phone screens have less micro-texture than real skin.

    Cue 2 – Laplacian focus score
        A real face seen by a webcam has natural blur from depth-of-field.
        A phone screen held in front has either very sharp edges (screen pixels)
        or very blurry edges (printed photo) — both differ from a real face.

    Cue 3 – Specular highlight check
        Real skin has soft specular highlights; a photo/screen has either none
        or very sharp bright spots.

    Returns True  → likely a live person  (allow attendance)
            False → likely a spoof attempt (reject)
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return True   # can't decode → don't block

    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_80 = _detect_and_crop_face(gray)
    if face_80 is None:
        return True   # no face detected → don't block recognition

    # ── Cue 1: LBP variance ─────────────────────────────────────────────────
    lbp_vec      = _compute_lbp(face_80)
    lbp_variance = float(np.var(lbp_vec))
    # Widened lower bound to 0.00010 — dim faces have less texture variance
    lbp_ok = 0.00010 <= lbp_variance <= 0.032

    # ── Cue 2: Laplacian (focus / sharpness) ────────────────────────────────
    lap_var = float(cv2.Laplacian(face_80, cv2.CV_64F).var())
    # Widened: dim lighting softens edges giving lower Laplacian scores
    focus_ok = 20 <= lap_var <= 1200

    # ── Cue 3: Specular highlight ratio ─────────────────────────────────────
    # Pixels brighter than 240 as fraction of face area
    bright_ratio = float(np.sum(face_80 > 240)) / (80 * 80)
    # Phone screens often have large overexposed areas (ratio > 0.15)
    # Printed photos under harsh light: < 0.01 or > 0.20
    spec_ok = bright_ratio < 0.18

    # Require at least 2 of 3 cues to pass (tolerant of edge lighting cases)
    score = int(lbp_ok) + int(focus_ok) + int(spec_ok)

    if score < 2:
        print(f"[LIVENESS FAIL] lbp_var={lbp_variance:.5f}({lbp_ok}) "
              f"lap={lap_var:.1f}({focus_ok}) bright={bright_ratio:.3f}({spec_ok})")
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
#  TRAINING
# ══════════════════════════════════════════════════════════════════════════════
def train_model_background(dataset_dir, update_status=None):
    print("\n TRAINING STARTED")

    X, y = [], []

    student_dirs = [
        s for s in os.listdir(dataset_dir)
        if os.path.isdir(os.path.join(dataset_dir, s))
    ]
    print(f"Found {len(student_dirs)} student folders")

    total = len(student_dirs)
    for idx, sid in enumerate(student_dirs):
        folder = os.path.join(dataset_dir, sid)
        images = [f for f in os.listdir(folder)
                  if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        valid  = 0

        for img_name in images:
            path = os.path.join(folder, img_name)
            img  = cv2.imread(path)
            if img is None:
                continue

            gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face_80 = _detect_and_crop_face(gray)

            if face_80 is None:
                # Fallback centre-crop — apply full normalisation pipeline
                h, w   = gray.shape
                size   = min(h, w)
                y0     = (h - size) // 2
                x0     = (w - size) // 2
                crop   = gray[y0:y0+size, x0:x0+size]
                face_80 = _normalise_lighting(cv2.resize(crop, (80, 80)))

            emb = _compute_lbp(face_80)

            if not np.isfinite(emb).all():
                print(f"  Skipping {img_name} — NaN in features")
                continue

            X.append(emb)
            y.append(int(sid))
            valid += 1

        pct = int((idx + 1) / total * 85)
        print(f"Student {sid}: {valid}/{len(images)} valid images")
        if update_status:
            update_status(pct, f"Processing student {sid} ({idx+1}/{total})")

    if len(X) < 10:
        print("Not enough data to train")
        if update_status:
            update_status(0, "Not enough data — add more students/images")
        return

    X = np.array(X, dtype=np.float32)
    y = np.array(y)

    if not np.isfinite(X).all():
        bad = np.sum(~np.isfinite(X))
        print(f"Warning: {bad} non-finite values — replacing with 0")
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    print(f"Total samples: {len(X)}")

    if update_status:
        update_status(87, "Normalising features...")

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)

    if update_status:
        update_status(90, "Training SVM classifier...")

    n_classes    = len(set(y.tolist()))
    class_counts = [int(np.sum(y == c)) for c in np.unique(y)]
    cv_folds     = max(2, min(5, min(class_counts)))

    base_clf = LinearSVC(C=1.5, max_iter=10000)   # slightly higher C for tighter boundary
    clf      = CalibratedClassifierCV(base_clf, cv=cv_folds, method="sigmoid")
    clf.fit(X_scaled, y)

    # Threshold: floor 0.48 so dim-lit faces (6 students → 2.0/6=0.33 → clamped 0.48) pass.
    threshold = round(min(0.80, max(0.48, 2.0 / n_classes)), 3)
    print(f"Auto-calibrated confidence threshold: {threshold}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump((clf, scaler, threshold), f)

    print("MODEL SAVED")
    if update_status:
        update_status(100, f"Training complete — {len(X)} samples, {n_classes} students")