from flask import Flask, request, jsonify, send_from_directory
import laspy
import numpy as np
import os, tempfile, threading, uuid, shutil

app = Flask(__name__)
GRID_SIZE = 1.0
jobs = {}  # job_id → {"status": "processing"/"done"/"error", ...}


def load_xyz(paths):
    xs, ys, zs = [], [], []
    for path in (paths if isinstance(paths, list) else [paths]):
        with laspy.open(path) as f:
            las = f.read()
            xs.append(np.array(las.x))
            ys.append(np.array(las.y))
            zs.append(np.array(las.z))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)


def compute_grid_mean_z(x, y, z, x_edges, y_edges):
    grid = {}
    xi = np.digitize(x, x_edges) - 1
    yi = np.digitize(y, y_edges) - 1
    valid = (xi >= 0) & (xi < len(x_edges) - 1) & (yi >= 0) & (yi < len(y_edges) - 1)
    for i in np.where(valid)[0]:
        key = (xi[i], yi[i])
        grid.setdefault(key, []).append(z[i])
    return {k: np.mean(v) for k, v in grid.items()}


def analyze(before_paths, after_paths):
    bx, by, bz = load_xyz(before_paths)
    ax, ay, az = load_xyz(after_paths)

    x_min = max(bx.min(), ax.min())
    x_max = min(bx.max(), ax.max())
    y_min = max(by.min(), ay.min())
    y_max = min(by.max(), ay.max())

    x_edges = np.arange(x_min, x_max + GRID_SIZE, GRID_SIZE)
    y_edges = np.arange(y_min, y_max + GRID_SIZE, GRID_SIZE)

    before_grid = compute_grid_mean_z(bx, by, bz, x_edges, y_edges)
    after_grid  = compute_grid_mean_z(ax, ay, az, x_edges, y_edges)

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
        result = analyze(before_paths, after_paths)
        jobs[job_id] = {"status": "done", "result": result}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/analyze", methods=["POST"])
def analyze_route():
    if "before" not in request.files or "after" not in request.files:
        return jsonify({"error": "before と after の両ファイルが必要です"}), 400

    job_id = str(uuid.uuid4())
    tmp = tempfile.mkdtemp(dir="D:\\")

    def save_all(key):
        paths = []
        for i, f in enumerate(request.files.getlist(key)):
            p = os.path.join(tmp, f"{key}_{i}.las")
            f.save(p)
            paths.append(p)
        return paths

    before_paths = save_all("before")
    after_paths  = save_all("after")

    jobs[job_id] = {"status": "processing"}
    threading.Thread(target=run_job, args=(job_id, before_paths, after_paths, tmp), daemon=True).start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status_route(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
