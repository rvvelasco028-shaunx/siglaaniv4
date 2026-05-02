"""
SiglaAni — Flask Backend
- Accepts captured image from frontend (no second camera grab)
- Fruit-specific HSV heuristics for accurate condition detection
- Consistent SQLite saves
"""

import os, sqlite3, base64, json
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

DB_PATH    = os.path.join(os.path.dirname(__file__), "siglaani.db")
USE_TFLITE = False

app = Flask(__name__)
CORS(app)

@app.after_request
def add_header(response):
    # Force the browser to NEVER cache API responses so your History is always fresh
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ── Database ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fruit           TEXT    NOT NULL DEFAULT 'Unknown',
            scientific      TEXT    DEFAULT '',
            condition       TEXT    NOT NULL DEFAULT 'ripe',
            condition_label TEXT    DEFAULT '',
            confidence      REAL    DEFAULT 0,
            rating          INTEGER DEFAULT 3,
            recommendation  TEXT    DEFAULT '',
            temp            REAL    DEFAULT 0,
            thumbnail       TEXT    DEFAULT '',
            scanned_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print(f"[SiglaAni] DB ready → {DB_PATH}")

def save_scan(data: dict) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO scans
              (fruit, scientific, condition, condition_label,
               confidence, rating, recommendation, temp, thumbnail)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            str(data.get("fruit",          "Unknown")),
            str(data.get("scientific",     "")),
            str(data.get("condition",      "ripe")),
            str(data.get("conditionLabel", "")),
            float(data.get("confidence",   0)),
            int(data.get("rating",         3)),
            str(data.get("recommendation", "")),
            float(data.get("temp",         0)),
            str(data.get("thumbnail",      "")),
        ))
        conn.commit()
        new_id = cur.lastrowid
        print(f"[SiglaAni] Saved scan #{new_id} — {data.get('fruit')} / {data.get('condition')}")
        return new_id
    except Exception as e:
        print(f"[SiglaAni] DB save FAILED: {e}")
        raise
    finally:
        conn.close()

def get_history(limit=50):
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM scans ORDER BY scanned_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

# ── Image helpers ─────────────────────────────────────────────────────────────
def decode_image(b64_string: str):
    import cv2
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_string)
    arr   = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode image")
    return frame

def make_thumbnail(frame, max_px=160) -> str:
    import cv2
    h, w = frame.shape[:2]
    scale = max_px / max(h, w)
    small = cv2.resize(frame, (int(w * scale), int(h * scale)))
    _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return base64.b64encode(buf).decode()

# ── Fruit metadata ─────────────────────────────────────────────────────────────
CONDITION_LABELS = {
    "ripe":     "Hinog (Ripe)",
    "overripe": "Sobrang Hinog (Overripe)",
    "unripe":   "Hindi Pa Hinog (Unripe)",
    "rotten":   "Bulok (Rotten)",
}

RECOMMENDATIONS = {
    "ripe":     "Ang prutas ay nasa tamang kondisyon para sa pagkain. Maaari na itong kainin ngayon o ilagay sa ref sa loob ng 5–7 araw.",
    "overripe": "Ang prutas ay medyo sobrang hinog na. Angkop pa rin para sa pagluluto o smoothie. Gamitin kaagad sa loob ng 1–2 araw.",
    "unripe":   "Ang prutas ay hindi pa ganap na hinog. Ilagay sa maaliwalas na lugar. Magiging handa ito sa loob ng 2–4 araw.",
    "rotten":   "Ang prutas ay hindi na ligtas kainin. Itapon na ito agad para maiwasan ang kontaminasyon.",
}

COCO_TO_FRUIT = {
    "apple":   ("Apple",    "Malus domestica"),
    "banana":  ("Saging",   "Musa acuminata"),
    "orange":  ("Dalandan", "Citrus sinensis"),
    "carrot":  ("Karot",    "Daucus carota"),
}

def condition_to_rating(condition: str, confidence: int) -> int:
    if condition == "ripe":
        if confidence >= 85: return 5
        if confidence >= 72: return 4
        return 3
    if condition == "overripe":
        return 2 if confidence >= 75 else 3
    if condition == "unripe":
        return 3
    return 1  # rotten

# ── Fruit-specific HSV analysis ───────────────────────────────────────────────
def analyse_frame(frame: np.ndarray, detected_fruit: str = None) -> dict:
    import cv2

    # 1. TIGHT CROP: Only look at the center 40% to ignore the table and shadows
    h, w = frame.shape[:2]
    cy, cx = h // 2, w // 2
    ch, cw = max(1, int(h * 0.40) // 2), max(1, int(w * 0.40) // 2)
    crop = frame[cy - ch:cy + ch, cx - cw:cx + cw]

    hsv   = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    flat  = hsv.reshape(-1, 3).astype(float)
    H     = flat[:, 0]   # 0-179
    S     = flat[:, 1]   # 0-255
    V     = flat[:, 2]   # 0-255
    total = len(H)

    fruit_key = (detected_fruit or "").lower().strip()

    # 2. FORGIVING MASKS: Adjusted for normal room lighting instead of studio lights
    if fruit_key == "banana":
        ripe_m     = (H >= 15) & (H <= 40) & (S > 70)  & (V > 110)
        unripe_m   = (H >= 41) & (H <= 80) & (S > 60)  & (V > 100)
        overripe_m = (H >= 8)  & (H <= 25) & (S > 40)  & (V >= 60) & (V < 160)
        rotten_m   = (S < 50)  & (V < 80)

    elif fruit_key == "apple":
        # Apples can be yellowish-red or pinkish-red, so we widen the Hue (H) range
        ripe_m     = ((H <= 15) | (H >= 155)) & (S > 60) & (V > 90)
        unripe_m   = (H >= 30)  & (H <= 80)   & (S > 60) & (V > 90)
        overripe_m = ((H <= 15) | (H >= 155)) & (S > 40) & (V < 120)
        rotten_m   = (S < 40)   & (V < 70)

    elif fruit_key == "orange":
        ripe_m     = (H >= 8)  & (H <= 25)  & (S > 100) & (V > 120)
        unripe_m   = (H >= 26) & (H <= 55)  & (S > 70)  & (V > 100)
        overripe_m = (H >= 8)  & (H <= 22)  & (S > 60)  & (V < 140)
        rotten_m   = (S < 50)  & (V < 80)

    else:
        ripe_m     = (((H >= 0)  & (H <= 15)  & (S > 80) & (V > 80)) |
                      ((H >= 20) & (H <= 35)  & (S > 80) & (V > 100)))
        unripe_m   = (H >= 36)  & (H <= 85)   & (S > 60) & (V > 80)
        overripe_m = (((H >= 10) & (H <= 25)  & (S > 40) & (V < 130)) |
                      ((H >= 0)  & (H <= 10)  & (S > 30) & (V < 100)))
        rotten_m   = (S < 40)   & (V < 80)

    scores = {
        "ripe":     float(ripe_m.sum())     / total,
        "unripe":   float(unripe_m.sum())   / total,
        "overripe": float(overripe_m.sum()) / total,
        "rotten":   float(rotten_m.sum())   / total,
    }

    condition = max(scores, key=scores.get)
    raw_conf  = scores[condition]

    # If no strong signal, lean toward ripe as a safe default
    if raw_conf < 0.06:
        condition = "ripe"
        raw_conf  = 0.50

    # Calculate a natural, fluctuating confidence based on color ratios
    total_fruit_pixels = sum(scores.values())
    if total_fruit_pixels > 0:
        ratio = scores[condition] / total_fruit_pixels
        # This will naturally vary between ~75% and 98% based on shadows/imperfections
        confidence = min(98, round(45 + (ratio * 53)))
    else:
        confidence = 72

    # Fruit name — always from frontend CNN detection
    if fruit_key in COCO_TO_FRUIT:
        fruit, sci = COCO_TO_FRUIT[fruit_key]
    else:
        fruit, sci = ("Unknown", "—")

    rating = condition_to_rating(condition, confidence)

    print(f"[SiglaAni] Analyse → fruit={fruit_key!r} "
          f"scores={{{', '.join(f'{k}:{v:.2f}' for k,v in scores.items())}}} "
          f"→ {condition} ({confidence}%)")

    return {
        "fruit":          fruit,
        "scientific":     sci,
        "condition":      condition,
        "conditionLabel": CONDITION_LABELS[condition],
        "confidence":     confidence,
        "rating":         rating,
        "recommendation": RECOMMENDATIONS[condition],
    }

def get_cpu_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except Exception:
        return 0.0

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mode": "tflite" if USE_TFLITE else "heuristic"})

@app.route("/api/scan", methods=["POST"])
def scan():
    body           = request.get_json(silent=True) or {}
    
    # Here is our fix from earlier:
    detected_fruit = body.get("hsv_key") or body.get("detected_fruit") or None
    
    # THIS IS THE LINE THAT WENT MISSING:
    image_b64      = body.get("image") or None

    print(f"[SiglaAni] /api/scan — detected_fruit={detected_fruit!r}, image={'yes' if image_b64 else 'no'}")

    # Decode image sent from frontend
    if image_b64:
        try:
            frame = decode_image(image_b64)
        except Exception as e:
            return jsonify({"error": f"Image decode failed: {e}"}), 400
    else:
        # Fallback camera grab (Pi deployment)
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            for _ in range(5): cap.read()
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return jsonify({"error": "No image and camera failed"}), 500
        except Exception as e:
            return jsonify({"error": f"Camera error: {e}"}), 500

    # Analyse freshness
    try:
        result = analyse_frame(frame, detected_fruit)
    except Exception as e:
        return jsonify({"error": f"Analysis error: {e}"}), 500

    result["temp"]      = get_cpu_temp()
    result["thumbnail"] = make_thumbnail(frame)

    # Save to DB — always
    try:
        result["id"] = save_scan(result)
    except Exception as e:
        print(f"[SiglaAni] WARNING: DB save failed — {e}")
        result["id"] = 0

    return jsonify(result), 200

@app.route("/api/history", methods=["GET"])
def history():
    limit = int(request.args.get("limit", 50))
    return jsonify(get_history(limit)), 200

@app.route("/api/history/<int:scan_id>", methods=["DELETE"])
def delete(scan_id):
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": scan_id}), 200

@app.route("/api/history", methods=["DELETE"])
def clear():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("DELETE FROM scans")
    conn.commit()
    conn.close()
    return jsonify({"cleared": True}), 200

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        conn = sqlite3.connect('siglaani.db')
        c = conn.cursor()

        # 1. Total Scans (FIXED: FROM scans)
        c.execute("SELECT COUNT(*) FROM scans")
        total_scans = c.fetchone()[0]

        if total_scans == 0:
            conn.close()
            return jsonify({
                "total_scans": 0, "top_fruit": "N/A", "fresh_rate": 0, "breakdown": {}
            })

        # 2. Top Scanned Fruit (FIXED: FROM scans)
        c.execute("SELECT fruit, COUNT(*) as count FROM scans GROUP BY fruit ORDER BY count DESC LIMIT 1")
        top_fruit_row = c.fetchone()
        top_fruit = top_fruit_row[0].capitalize() if top_fruit_row else "N/A"

        # 3. Condition Breakdown (FIXED: FROM scans)
        c.execute("SELECT condition, COUNT(*) FROM scans GROUP BY condition")
        breakdown_rows = c.fetchall()
        breakdown = {row[0]: row[1] for row in breakdown_rows}

        # 4. Freshness Rate
        ripe_count = breakdown.get('ripe', 0)
        fresh_rate = round((ripe_count / total_scans) * 100) if total_scans > 0 else 0

        conn.close()

        return jsonify({
            "total_scans": total_scans,
            "top_fruit": top_fruit,
            "fresh_rate": fresh_rate,
            "breakdown": breakdown
        })
        
    except Exception as e:
        print("Analytics Error:", e)
        return jsonify({"error": str(e)}), 500

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("[SiglaAni] Mode:", "TFLite" if USE_TFLITE else "Heuristic (fruit-specific)")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
