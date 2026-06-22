from flask import Flask, request, jsonify, send_from_directory
import laspy
import numpy as np
import os, tempfile, threading, uuid, shutil

app = Flask(__name__)
GRID_SIZE = 1.0
jobs     = {}  # job_id     → {"status": "processing"/"done"/"error", ...}
sessions = {}  # session_id → {"before": [...paths], "after": [...paths], "tmp": "..."}


def get_bounds(paths, job_id, label):
    total = len(paths)
    x_min, x_max, y_min, y_max = np.inf, -np.inf, np.inf, -np.inf
    for i, path in enumerate(paths):
        jobs[job_id]["detail"] = f"[境界取得] {label}: {i+1} / {total} ファイル"
        with laspy.open(path) as f:
            hdr = f.header
            x_min = min(x_min, float(hdr.x_min))
            x_max = max(x_max, float(hdr.x_max))
            y_min = min(y_min, float(hdr.y_min))
            y_max = max(y_max, float(hdr.y_max))
    return x_min, x_max, y_min, y_max


def build_grid(paths, x_edges, y_edges, job_id, label, offset, total_files):
    nx = len(x_edges) - 1
    ny = len(y_edges) - 1
    z_sum = np.zeros(nx * ny)
    z_cnt = np.zeros(nx * ny, dtype=np.int32)
    n = len(paths)
    for i, path in enumerate(paths):
        jobs[job_id]["detail"] = f"[グリッド構築] {label}: {i+1} / {n} ファイル"
        jobs[job_id]["pct"]    = int((offset + i + 1) / total_files * 100)
        with laspy.open(path) as f:
            las = f.read()
            x = np.array(las.x)
            y = np.array(las.y)
            z = np.array(las.z)
        xi = np.digitize(x, x_edges) - 1
        yi = np.digitize(y, y_edges) - 1
        valid = (xi >= 0) & (xi < nx) & (yi >= 0) & (yi < ny)
        flat = xi[valid] * ny + yi[valid]
        zv   = z[valid]
        z_sum += np.bincount(flat, weights=zv, minlength=nx * ny)
        z_cnt += np.bincount(flat,              minlength=nx * ny).astype(np.int32)
    nonzero = np.where(z_cnt > 0)[0]
    return {(int(i // ny), int(i % ny)): float(z_sum[i] / z_cnt[i]) for i in nonzero}


def analyze(before_paths, after_paths, job_id):
    nb, na = len(before_paths), len(after_paths)
    total_files = nb + na

    jobs[job_id]["detail"] = "[境界取得] 開始..."
    bx_min, bx_max, by_min, by_max = get_bounds(before_paths, job_id, "災害前")
    ax_min, ax_max, ay_min, ay_max = get_bounds(after_paths,  job_id, "災害後")

    x_min = max(bx_min, ax_min)
    x_max = min(bx_max, ax_max)
    y_min = max(by_min, ay_min)
    y_max = min(by_max, ay_max)

    x_edges = np.arange(x_min, x_max + GRID_SIZE, GRID_SIZE)
    y_edges = np.arange(y_min, y_max + GRID_SIZE, GRID_SIZE)

    before_grid = build_grid(before_paths, x_edges, y_edges, job_id, "災害前", 0,  total_files)
    after_grid  = build_grid(after_paths,  x_edges, y_edges, job_id, "災害後", nb, total_files)

    jobs[job_id]["detail"] = "[差分計算] 危険度マップ生成中..."
    jobs[job_id]["pct"]    = 99

    common_keys = set(before_grid) & set(after_grid)
    if not common_keys:
        return {"type": "FeatureCollection", "features": []}

    deltas = {k: abs(after_grid[k] - before_grid[k]) for k in common_keys}
    d_vals = np.array(list(deltas.values()))
    d_min, d_max = d_vals.min(), d_vals.max()

    def to_danger(d):
        if d_max == d_min:
            return 5
        return int(1 + 9 * (d - d_min) / (d_max - d_min))

    features = []
    for (xi, yi), delta in deltas.items():
        cx = x_edges[xi] + GRID_SIZE / 2
        cy = y_edges[yi] + GRID_SIZE / 2
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [cx, cy]},
            "properties": {"danger": to_danger(delta), "delta_z": round(float(delta), 3)}
        })

    return {"type": "FeatureCollection", "features": features}


def run_job(job_id, before_paths, after_paths, tmp_dir):
    try:
        result = analyze(before_paths, after_paths, job_id)
        jobs[job_id] = {"status": "done", "result": result}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    session_id = request.form.get("session_id")
    file_type  = request.form.get("type")
    file       = request.files.get("file")

    if not session_id or file_type not in ("before", "after") or not file:
        return jsonify({"error": "invalid request"}), 400

    if session_id not in sessions:
        sessions[session_id] = {
            "before": [], "after": [],
            "tmp": tempfile.mkdtemp(dir="D:\\")
        }

    bucket = sessions[session_id][file_type]
    path = os.path.join(sessions[session_id]["tmp"], f"{file_type}_{len(bucket)}.las")
    file.save(path)
    bucket.append(path)

    return jsonify({"ok": True})


@app.route("/analyze", methods=["POST"])
def analyze_route():
    data = request.get_json()
    session_id = data.get("session_id") if data else None

    if not session_id or session_id not in sessions:
        return jsonify({"error": "セッションが見つかりません"}), 400

    session      = sessions.pop(session_id)
    before_paths = session["before"]
    after_paths  = session["after"]
    tmp_dir      = session["tmp"]

    if not before_paths or not after_paths:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": "ファイルが不足しています"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "pct": 0, "detail": "準備中..."}
    threading.Thread(target=run_job, args=(job_id, before_paths, after_paths, tmp_dir), daemon=True).start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status_route(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
