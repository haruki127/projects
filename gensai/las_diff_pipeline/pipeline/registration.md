# ================================================================
icp_registration.py　コード解説（コード ｜ 解説 の対応形式）

# 左側がコード、右側（→以降）がその解説です。

---

## 【ファイル冒頭・インポート】

"""ICP registration (Open3D primary, scipy fallback)."""
→ このファイルの説明メモ（Open3Dを最優先に使い、なければSciPyで位置合わせを行う）。

from **future** import annotations           → 型ヒントの書き方を新しいスタイルに統一するおまじない。

import logging                               → 動作記録（ログ）を残すための道具箱を読み込む。
from pathlib import Path                     → ファイルのパス（場所）を扱いやすくする道具を読み込む。

import numpy as np                           → 大量の数値を高速に計算するライブラリを「np」という名前で読み込む。

from .io_las import PointCloud               → 最初に作った `io_las.py` から点群データ管理用の「PointCloud」クラスを読み込む。

logger = logging.getLogger(**name**)         → このファイル専用のログ出力係を作る。

---

## 【_load_stable_mask 関数】　地殻変動などの影響を受けない「安定地域」のマスクを読み込む

def _load_stable_mask(path):
→ 動いていない場所（道路や建物など）を指定した地図データ（シェープファイルなど）を読み込む関数。
try:                                     → geopandasがインストールされているか試みる。
import geopandas as gpd              → 地図データを扱うライブラリ（GeoPandas）を読み込む。
except ImportError as e:                 → インストールされていなかった場合のエラー処理。
raise ImportError("geopandas is required for stable_mask") from e
→ 分かりやすいエラーメッセージを出して終了する。
return gpd.read_file(path)               → 地図データ（ポリゴンデータなど）を読み込んで返す。

---

## 【_mask_points_in_polygons 関数】　ポリゴン（範囲）の内側にある点群だけを抜き出す

def _mask_points_in_polygons(xyz, gdf, epsg):
→ 点群（xyz）のうち、地図データ（gdf）の範囲内にある点だけに絞るための関数。
from shapely.geometry import Point       → 1つの「点」を定義するためのジオメトリの道具を読み込む。
if gdf.crs is None:                      → 地図データに座標系の設定がない場合。
logger.warning("stable_mask has no CRS; assuming EPSG:%d", epsg)
→ 「座標系がないため、点群と同じ座標系だと仮定します」と警告を出す。
gdf = gdf.set_crs(epsg=epsg)         → 強制的に点群と同じEPSG番号を設定する。
elif gdf.crs.to_epsg() != epsg:          → 地図データと点群データの座標系（EPSG番号）が違っていた場合。
gdf = gdf.to_crs(epsg=epsg)          → 地図データの座標系を点群データのものに自動で変換（リプロジェクション）する。
union = gdf.unary_union                  → 複数のポリゴン（範囲）を1つの大きな範囲に合体させる。
mask = np.array([union.contains(Point(p[0], p[1])) for p in xyz], dtype=bool)
→ すべての点について「範囲の内側にあるか？」をTrue/Falseの配列にする。
logger.info("Stable mask: %d / %d points inside", int(mask.sum()), len(xyz))
→ 範囲内に何点あったかをログに記録する。
return mask                              → True/Falseの結果（マスク配列）を返す。

---

## 【icp_align 関数】　2つの点群の位置合わせを行うメイン関数

def icp_align(source: PointCloud, target: PointCloud,
stable_mask_path=None, max_iterations: int = 50, threshold: float = 0.5):
→ 動かしたい点群（source）と、基準にする点群（target）をぴったり重ね合わせるメイン関数。
if source.crs_epsg != target.crs_epsg:   → 2つの点群の座標ルール（EPSG）が一致していない場合。
raise ValueError("CRS must match before ICP")
→ 「先に座標系を揃えてください」とエラーを出して終了する。

```
if stable_mask_path is not None:         → 安定地域（マスク）のファイルが指定されている場合。
    gdf = _load_stable_mask(stable_mask_path) → 地図データを読み込む。
    m_src = _mask_points_in_polygons(source.xyz, gdf, source.crs_epsg)  → 動かしたい点群から範囲内の点を判定。
    m_tgt = _mask_points_in_polygons(target.xyz, gdf, target.crs_epsg)  → 基準の点群から範囲内の点を判定。
    src_xyz = source.xyz[m_src]          → 範囲内にある「動かしたい点群」だけを抽出。
    tgt_xyz = target.xyz[m_tgt]          → 範囲内にある「基準の点群」だけを抽出。
else:                                    → マスクが指定されていない場合。
    logger.warning("stable_mask not provided. Using all points; displaced regions may bias.")
                                         → 「すべての点を使います。地滑りなどで動いた地形があるとズレの原因になります」と警告。
    src_xyz = source.xyz                 → 元の点群をそのまま計算に使う。
    tgt_xyz = target.xyz                 → 基準の点群をそのまま計算に使う。

if len(src_xyz) < 100 or len(tgt_xyz) < 100: → 計算に使う点が100点未満と少なすぎる場合。
    raise RuntimeError("Too few points for ICP")
                                         → 「点数が少なすぎて位置合わせができません」とエラーを出す。

try:                                     → まずは最優先のライブラリを使えるか試みる。
    import open3d  # noqa: F401          → Open3Dがインストールされているか確認。
    T = _icp_open3d(src_xyz, tgt_xyz, max_iterations, threshold)
                                         → Open3Dを使った高速なICP位置合わせを実行し、変換行列（T）を得る。
except ImportError:                      → Open3Dが入っていなかった場合。
    logger.info("open3d not available; using scipy-based ICP fallback")
                                         → 「Open3Dがないため、SciPyを使った自前計算に切り替えます」と記録。
    T = _icp_scipy(src_xyz, tgt_xyz, max_iterations, threshold)
                                         → SciPyベースのバックアップ処理（自前ICP）を実行し、変換行列（T）を得る。

homo = np.column_stack([source.xyz, np.ones(source.n)])
                                         → 座標変換の計算をしやすくするため、点群の右側に「1」の列を合体させる（同次座標系）。
new_xyz = (homo @ T.T)[:, :3]            → 行列計算を使って、動かしたい点群のすべてのXYZ座標を新しい位置へ一括変換する。
aligned = PointCloud(xyz=new_xyz, classification=source.classification,
                     intensity=source.intensity, crs_epsg=source.crs_epsg, extras=source.extras)
                                         → 位置移動した新しい座標を、元の分類や強度データと一緒に新しいPointCloudとしてまとめる。
return aligned, T                        → 位置合わせ済みの点群データと、どのように動かしたかの移動情報（行列T）を返す。

```

---

## 【_icp_open3d 関数】　Open3Dライブラリを使った高速な位置合わせ

def _icp_open3d(src_xyz, tgt_xyz, max_iter, threshold):
→ Open3Dライブラリを用いて最適化計算を行う関数。
import open3d as o3d                     → Open3Dを読み込む。
src = o3d.geometry.PointCloud(); src.points = o3d.utility.Vector3dVector(src_xyz)
→ 動かしたい点群をOpen3D専用のデータ形式に変換する。
tgt = o3d.geometry.PointCloud(); tgt.points = o3d.utility.Vector3dVector(tgt_xyz)
→ 基準の点群をOpen3D専用のデータ形式に変換する。
result = o3d.pipelines.registration.registration_icp(
src, tgt, max_correspondence_distance=threshold, init=np.eye(4),
estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
criteria=o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=max_iter),
)
→ Open3DのICP機能を呼び出す。
→   max_correspondence_distance=threshold（この距離以内の近い点同士を対応付ける）。
→   init=np.eye(4)（最初は動かさない状態からスタート）。
→   PointToPoint（点と点の間が一番近くなるように計算するモード）。
→   max_iteration=max_iter（最大で何回繰り返し計算するか）。
logger.info("ICP(open3d) fitness=%.4f rmse=%.4f", result.fitness, result.inlier_rmse)
→ 重なり具合（fitness）と平均誤差（rmse）をログに記録する。
return np.asarray(result.transformation) → 計算された4x4の変換行列（回転と平行移動の情報）をNumPyの配列にして返す。

---

## 【_icp_scipy 関数】　Open3Dがない場合の自前位置合わせ（バックアップ用）

def _icp_scipy(src_xyz, tgt_xyz, max_iter, threshold):
"""scipy.cKDTree ベースの自前 point-to-point ICP (Umeyama 法)."""
→ Open3Dが環境にないときのために、数学的（特異値分解: SVDなど）に自前でICPを再現した関数。
from scipy.spatial import cKDTree        → 近くにある点群をものすごく高速に探し出せる道具（KD木）を読み込む。
max_pts = 200_000                        → 計算が重くならないように、一度に扱う最大点数を20万点に制限する。
rs = np.random.RandomState(42)           → 毎回同じランダムな選び方になるようにシード（42番）を固定。
if len(src_xyz) > max_pts:               → 動かしたい点群が20万点を超えて多すぎる場合。
idx = rs.choice(len(src_xyz), max_pts, replace=False)
→ ランダムに20万点だけを重複なしで選ぶ（ダウンサンプリング）。
src = src_xyz[idx].astype(np.float64) → 選ばれた点だけを精密な小数データとして準備。
else:
src = src_xyz.astype(np.float64)     → 20万点以下ならすべてそのまま使う。
tgt = tgt_xyz.astype(np.float64)         → 基準の点群を小数データとして準備。
tree = cKDTree(tgt)                      → 基準の点群をKD木に登録して、いつでも最寄りの点を探せるようにする。

```
T = np.eye(4); prev_rmse = np.inf; last_it = 0
                                         → 初期設定（T = 変形なしの行列、前回の誤差 = 無限大、回数カウンター）。
for it in range(max_iter):               → 指定された最大回数まで、位置調整を少しずつ繰り返す（ループ）。
    src_h = np.column_stack([src, np.ones(len(src))]) → 計算用に行列の右側に「1」を足す。
    cur = (src_h @ T.T)[:, :3]            → 現在の変換行列「T」を使って、点群を少し動かしてみる。
    d, idx = tree.query(cur, distance_upper_bound=threshold * 5.0)
                                         → 動かした点群から見て、基準点群の「一番近い点」とその距離（d）を検索する。
                                         →   distance_upper_bound = 離れすぎている点（しきい値の5倍以上）は無視する。
    good = np.isfinite(d) & (d < threshold * 5.0)
                                         → ちゃんと近くの相手が見つかった「正しい対応点」だけを絞り込む。
    if good.sum() < 100:                 → 正しい対応点が100点未満になってしまった場合。
        break                            → 位置合わせ不能としてループを抜ける。
    s = cur[good]; t = tgt[idx[good]]    → 絞り込んだ、動かしたい点群（s）と、対応する基準の点群（t）をセットにする。
    sm = s.mean(axis=0); tm = t.mean(axis=0) → それぞれのグループの「中心点（平均座標）」を計算する。
    U, _, Vt = np.linalg.svd((s - sm).T @ (t - tm))
                                         → 中心を揃えた点群同士のズレを「特異値分解(SVD)」という高度な数学手法で分解する。
    D = np.eye(3)                        → 反転（鏡像）を防ぐための補正用行列を準備する。
    if np.linalg.det(Vt.T @ U.T) < 0:    → 計算結果が反転してしまっている場合。
        D[2, 2] = -1                     → 反転を打ち消す設定にする。
    R = Vt.T @ D @ U.T                   → これにより、一番ズレが少なくなる「最適な回転（向き）」が決定する。
    tr = tm - R @ sm                     → 「最適な移動量（平行移動）」を計算する。
    dT = np.eye(4); dT[:3, :3] = R; dT[:3, 3] = tr
                                         → 今回のステップで動かす分の4x4変換行列を作る。
    T = dT @ T                           → これまでの全体の移動情報に、今回の移動分を掛け合わせて更新する。
    rmse = float(np.sqrt((d[good] ** 2).mean()))
                                         → 現在の対応点同士の平均的なズレ（誤差: RMSE）を計算する。
    last_it = it                         → 現在のループ回数を記録。
    if abs(prev_rmse - rmse) < 1e-4:     → 前回計算した時と比べて、誤差がほとんど減らなくなった（0.0001m未満）場合。
        break                            → 「もう限界までぴったり重なった」と判断してループを終了する。
    prev_rmse = rmse                     → 今回の誤差を「前回の誤差」として保存し、次のループへ進む。

logger.info("ICP(scipy) iters=%d rmse=%.4f", last_it + 1, prev_rmse)
                                         → 何回繰り返して、最終的にどれくらいの誤差になったかをログに記録する。
return T                                 → 計算し尽くした最終的な変換行列（T）を返す。

```

# ================================================================
全体の処理の流れ（まとめ）

[動かしたい点群 (source) ] 　 [基準にする点群 (target) ]
│                            │
▼                            ▼

1. マスク処理（オプション）
・地滑り等で動いていない「安定地域（建物や道路）」の地図がある場合、
その範囲内にある点群だけに絞り込む（動いた地形に引っ張られてズレるのを防ぐ）。
│                            │
└──────────┬──────────┘
▼
2. 点数のチェック
・計算に十分な点数（100点以上）が存在するか確認する。
▼
3. ICPアルゴリズムの自動判別と実行（繰り返し最適化）
・【Open3Dがある場合】: ライブラリに任せて超高速に位置合わせ（最適化）。
・【Open3Dがない場合】: SciPyと数学計算（SVD）を使って、自前で少しずつ
回転と移動を繰り返してズレを最小化する（バックアップ処理）。
▼
4. 変換行列（T）の決定
・一番きれいに重なる「4x4の回転・移動パラメータ」が確定する。
▼
5. 点群の変形と出力
・確定した行列を使って、動かしたい点群全体の座標を一括で移動。
・位置合わせ完了後の「新しいPointCloud」と「変換行列（T）」をセットで返す。

================================================================
