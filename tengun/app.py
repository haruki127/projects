from flask import Flask, request, jsonify, send_from_directory
import laspy
import numpy as np
import os, tempfile

app = Flask(__name__)
GRID_SIZE = 1.0  # グリッドサイズ（メートル相当）


def load_xyz(path):
    """LASファイルからXYZ座標を読み込む"""
    las = laspy.read(path)
    x = np.array(las.x)
    y = np.array(las.y)
    z = np.array(las.z)
    return x, y, z


def compute_grid_mean_z(x, y, z, x_edges, y_edges):
    """各グリッドセルの平均Z値を計算する"""
    grid = {}
    xi = np.digitize(x, x_edges) - 1
    yi = np.digitize(y, y_edges) - 1
    valid = (xi >= 0) & (xi < len(x_edges) - 1) & (yi >= 0) & (yi < len(y_edges) - 1)
    for i in np.where(valid)[0]:
        key = (xi[i], yi[i])
        grid.setdefault(key, []).append(z[i])
    return {k: np.mean(v) for k, v in grid.items()}


def analyze(before_path, after_path):
    """2つのLASファイルを比較しGeoJSONを返す"""
    bx, by, bz = load_xyz(before_path)
    ax, ay, az = load_xyz(after_path)

    # 共通範囲でグリッドを作成
    x_min = max(bx.min(), ax.min())
    x_max = min(bx.max(), ax.max())
    y_min = max(by.min(), ay.min())
    y_max = min(by.max(), ay.max())

    x_edges = np.arange(x_min, x_max + GRID_SIZE, GRID_SIZE)
    y_edges = np.arange(y_min, y_max + GRID_SIZE, GRID_SIZE)

    before_grid = compute_grid_mean_z(bx, by, bz, x_edges, y_edges)
    after_grid = compute_grid_mean_z(ax, ay, az, x_edges, y_edges)

    # 共通セルのΔZを計算
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
        danger = to_danger(delta)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [cx, cy]},
            "properties": {"danger": danger, "delta_z": round(float(delta), 3)}
        })

    return {"type": "FeatureCollection", "features": features}


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/analyze", methods=["POST"])
def analyze_route():
    if "before" not in request.files or "after" not in request.files:
        return jsonify({"error": "before と after の両ファイルが必要です"}), 400

    with tempfile.TemporaryDirectory() as tmp:
        before_path = os.path.join(tmp, "before.las")
        after_path = os.path.join(tmp, "after.las")
        request.files["before"].save(before_path)
        request.files["after"].save(after_path)
        try:
            result = analyze(before_path, after_path)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
