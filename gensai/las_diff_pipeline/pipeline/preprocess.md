================================================================
  preprocessing.py　コード解説（コード ｜ 解説 の対応形式）
================================================================
左側がコード、右側（→以降）がその解説です。
================================================================


----------------------------------------------------------------
【ファイル冒頭・インポート】
----------------------------------------------------------------

"""Preprocessing: reprojection, bbox clip,               → このファイルの説明メモ。
   SOR, voxel downsample, ground filter."""              →   reprojection（座標変換）、clip（切り取り）など
                                                         →   このファイルで行う処理の一覧を書いている。

from __future__ import annotations                       → 型ヒントの書き方を新しいスタイルに統一するおまじない。

import logging                                           → ログ（動作記録）を残すための道具箱を読み込む。

import numpy as np                                       → 大量の数値を高速に計算するライブラリを「np」という名前で読み込む。

from .io_las import PointCloud                           → 同じフォルダの io_las.py から PointCloud クラスを読み込む。
                                                         →   「.」は「同じフォルダの中」を意味する。

logger = logging.getLogger(__name__)                     → このファイル専用のログ出力係を作る。


----------------------------------------------------------------
【reproject 関数】　座標系を変換する
----------------------------------------------------------------

def reproject(pc: PointCloud, target_epsg: int) -> PointCloud:
                                                         → 座標系を変換する関数。
                                                         →   pc          = 変換前の点群データ（PointCloud）。
                                                         →   target_epsg = 変換先の座標系のEPSG番号（整数）。
                                                         →   -> PointCloud = 変換後のPointCloudを返す。

    if pc.crs_epsg == target_epsg or \                   → 以下の3つのどれかに当てはまる場合、変換不要と判断する。
       pc.crs_epsg is None or \
       target_epsg is None:
                                                         →   pc.crs_epsg == target_epsg → すでに同じ座標系。
                                                         →   pc.crs_epsg is None        → 元データに座標系情報がない。
                                                         →   target_epsg is None        → 変換先が指定されていない。
        return pc                                        →   変換不要なのでそのままデータを返して終了する。

    try:                                                 → pyproj が使えるか試みる。
        import pyproj                                    →   座標変換専門のライブラリを読み込む。
    except ImportError as e:                             → pyproj がインストールされていなかった場合。
        raise ImportError("pyproj required for reprojection") from e
                                                         →   わかりやすいメッセージのエラーを出して終了する。

    logger.info("Reprojecting EPSG:%d -> EPSG:%d",      → 「EPSG:〇〇 → EPSG:〇〇 に変換中」とログに記録する。
                pc.crs_epsg, target_epsg)               →   %d は整数を埋め込むプレースホルダー（穴埋め）。

    tr = pyproj.Transformer.from_crs(                   → 座標変換器「tr」を作る。
        pc.crs_epsg, target_epsg, always_xy=True)       →   from_crs(元の座標系, 変換先座標系) で変換ルールを設定。
                                                         →   always_xy=True = 必ずX（経度）→Y（緯度）の順で扱う指定。

    x, y = tr.transform(pc.xyz[:, 0], pc.xyz[:, 1])    → 実際にX・Y座標を変換する。
                                                         →   pc.xyz[:, 0] = 全点のX座標（0列目）。
                                                         →   pc.xyz[:, 1] = 全点のY座標（1列目）。
                                                         →   [:] は「全行」を意味するスライス記法。

    new_xyz = np.column_stack([x, y, pc.xyz[:, 2]])     → 変換後X・Y と変換前のZ（高さ）を横に並べて新しい配列を作る。
                                                         →   Z（高さ）は座標変換の影響を受けないのでそのまま使う。

    return PointCloud(xyz=new_xyz,                       → 変換後の座標で新しい PointCloud を作って返す。
                      classification=pc.classification, →   分類番号はそのまま引き継ぐ。
                      intensity=pc.intensity,           →   反射強度はそのまま引き継ぐ。
                      crs_epsg=target_epsg,             →   EPSG番号だけ新しい座標系番号に更新する。
                      extras=pc.extras)                 →   追加データはそのまま引き継ぐ。


----------------------------------------------------------------
【clip_bbox 関数】　四角形の範囲外の点を削除する
----------------------------------------------------------------

def clip_bbox(pc: PointCloud, bbox) -> PointCloud:      → 範囲外の点を削除する関数。
                                                         →   bbox = 切り取る範囲（minX, minY, maxX, maxY の4つの数値）。

    minx, miny, maxx, maxy = bbox                       → bbox の4つの値をそれぞれ変数に分解して取り出す。
                                                         →   minx・miny = 範囲の左下の座標。
                                                         →   maxx・maxy = 範囲の右上の座標。

    x, y = pc.xyz[:, 0], pc.xyz[:, 1]                  → 全点のX座標とY座標を取り出す。

    m = (x >= minx) & (x <= maxx) & \                   → 各点が範囲内かどうかを True / False で判定した配列を作る。
        (y >= miny) & (y <= maxy)                       →   & は「かつ（AND）」の意味。
                                                         →   4つの条件を全て満たす点だけ True になる。

    n_in = int(m.sum())                                  → True の数（範囲内に残る点の数）を数える。
    logger.info("Clip bbox: %d / %d points kept",       → 「〇〇点中〇〇点を残しました」とログに記録する。
                n_in, len(pc.xyz))

    return PointCloud(xyz=pc.xyz[m],                     → True の点だけ残した新しい PointCloud を返す。
                                                         →   pc.xyz[m] = m が True の行だけ取り出す（ブールインデックス）。
        classification=pc.classification[m] \           →   分類番号も同じ条件でフィルタリングする。
            if pc.classification is not None else None, →   データがない場合は None のまま。
        intensity=pc.intensity[m] \                     →   反射強度も同じ条件でフィルタリングする。
            if pc.intensity is not None else None,      →   データがない場合は None のまま。
        crs_epsg=pc.crs_epsg, extras=pc.extras)         →   座標系と追加データはそのまま引き継ぐ。


----------------------------------------------------------------
【sor_filter 関数】　ノイズ点を除去する（統計的外れ値除去）
----------------------------------------------------------------

def sor_filter(pc: PointCloud, k: int = 16,             → ノイズ点を除去する関数。
               z_thresh: float = 2.0) -> PointCloud:    →   k        = 近傍の点を何個調べるか（デフォルト16個）。
                                                         →   z_thresh = 何標準偏差離れたら除去するか（デフォルト2.0）。
    """Statistical Outlier Removal                       → この関数の説明メモ。
    (近傍距離が mean+z*std を超えた点を除去)."""          →   SOR = Statistical Outlier Removal（統計的外れ値除去）。

    try:                                                 → scipy が使えるか試みる。
        from scipy.spatial import cKDTree               →   cKDTree = 近い点を高速に探せるデータ構造。
    except ImportError as e:                             → インストールされていなかった場合。
        raise ImportError("scipy required for SOR") from e
                                                         →   わかりやすいメッセージのエラーを出して終了する。

    if len(pc.xyz) < k + 1:                             → 点の総数が k+1 より少ない場合。
        return pc                                        →   計算できないのでそのまま返して終了する。

    logger.info("SOR filter: k=%d, z=%.1f", k, z_thresh)
                                                         → 「SORフィルタ開始。k=〇〇、z=〇〇」とログに記録する。

    tree = cKDTree(pc.xyz)                              → 全点を使って近傍探索用の木構造（KDTree）を作る。
                                                         →   KDTree = 近い点を素早く見つけるためのデータ整理方法。

    d, _ = tree.query(pc.xyz, k=k + 1)                 → 各点から近い順に k+1 個の点との距離を調べる。
                                                         →   自分自身（距離0）も含まれるので k+1 個調べる。
                                                         →   d = 距離の配列、_ = インデックス（今回は使わない）。

    md = d[:, 1:].mean(axis=1)                          → 自分自身（1列目）を除いた k 個との平均距離を計算する。
                                                         →   d[:, 1:] = 2列目以降（自分を除く）を取り出す。
                                                         →   mean(axis=1) = 各行（各点）ごとの平均を取る。

    th = md.mean() + z_thresh * md.std()                → 除去の閾値（基準）を計算する。
                                                         →   md.mean() = 全点の平均距離の平均。
                                                         →   md.std()  = 全点の平均距離の標準偏差（ばらつき）。
                                                         →   閾値 = 平均 + z_thresh × 標準偏差。

    keep = md <= th                                      → 閾値以下の点だけ True にした配列を作る（True = 残す点）。

    n_in = int(keep.sum())                               → 残る点の数を数える。
    logger.info("  %d / %d kept (thresh=%.3f)",         → 「〇〇点中〇〇点を残しました（閾値=〇〇）」とログに記録する。
                n_in, len(pc.xyz), th)

    return PointCloud(xyz=pc.xyz[keep],                  → True の点だけ残した新しい PointCloud を返す。
        classification=pc.classification[keep] \        →   分類番号も同じ条件でフィルタリングする。
            if pc.classification is not None else None,
        intensity=pc.intensity[keep] \                  →   反射強度も同じ条件でフィルタリングする。
            if pc.intensity is not None else None,
        crs_epsg=pc.crs_epsg, extras=pc.extras)         →   座標系と追加データはそのまま引き継ぐ。


----------------------------------------------------------------
【voxel_downsample 関数】　点を間引いてデータ量を減らす
----------------------------------------------------------------

def voxel_downsample(pc: PointCloud,                    → 点を間引く関数。
                     voxel_size: float) -> PointCloud:  →   voxel_size = ボクセル（立方体マス）の1辺の大きさ（メートル）。
    """ボクセル間引き (各 voxel の重心を代表点)."""      → この関数の説明メモ。ボクセルごとの重心を代表点にする。

    if voxel_size is None or voxel_size <= 0:           → voxel_size が指定されていないか0以下の場合。
        return pc                                        →   処理不要なのでそのまま返して終了する。

    logger.info("Voxel downsample: %.3fm", voxel_size)  → 「ボクセル間引き開始。〇〇m」とログに記録する。

    xyz = pc.xyz                                         → 座標配列を xyz という短い変数名で扱えるようにする。

    ix = np.floor(xyz / voxel_size).astype(np.int64)   → 各点がどのボクセルに入るかを整数インデックスで計算する。
                                                         →   floor = 小数点以下切り捨て（例：2.7 → 2）。
                                                         →   これで空間を格子状のマス目に分割できる。

    # 一意なキーで集約
    key = ix[:, 0].astype(np.int64) * 73856093 \        → 各点のボクセルを1つの整数キーに変換する。
          ^ ix[:, 1] * 19349663 \                       →   X・Y・Z のインデックスを大きな素数で掛けてXOR（^）で合成。
          ^ ix[:, 2] * 83492791                         →   これにより異なるボクセルは異なるキーになる（ハッシュ）。

    order = np.argsort(key)                              → キーを小さい順に並べ替えたときのインデックスを取得する。
    ks = key[order]                                      → キーを並べ替えた配列。
    xs = xyz[order]                                      → 座標もキーと同じ順番で並べ替えた配列。

    u, first = np.unique(ks, return_index=True)         → 重複なしのキー一覧と、それぞれの最初の位置を取得する。
                                                         →   u     = ユニークなキーの配列。
                                                         →   first = 各ユニークキーが最初に現れる位置。

    sums = np.add.reduceat(xs, first, axis=0)           → 各ボクセルに属する点の座標の合計を計算する。
                                                         →   reduceat = 指定した区切りごとに集計する関数。

    counts = np.diff(np.append(first, len(ks)))         → 各ボクセルに何点入っているか数える。
                                                         →   append で末尾に総数を追加し、diff で差分を取る。

    centroids = sums / counts[:, None]                   → 合計 ÷ 点数 = ボクセルごとの重心（平均座標）を計算する。
                                                         →   counts[:, None] = 割り算できるよう列方向に次元を追加。

    logger.info("  %d -> %d points",                    → 「〇〇点 → 〇〇点に削減しました」とログに記録する。
                len(xyz), len(centroids))

    return PointCloud(xyz=centroids,                     → 重心座標だけを持つ新しい PointCloud を返す。
                      crs_epsg=pc.crs_epsg,             →   座標系はそのまま引き継ぐ。
                      extras=pc.extras)                 →   追加データはそのまま引き継ぐ。
                                                         →   ※間引き後は各点の対応が不明なため分類・強度は引き継がない。


----------------------------------------------------------------
【classify_ground 関数】　地面の点だけを抽出する
----------------------------------------------------------------

def classify_ground(pc: PointCloud,                     → 地面の点だけ残す関数。
                    cell_size: float = 1.0) -> PointCloud:
                                                         →   cell_size = グリッド（格子）の1マスの大きさ（デフォルト1m）。
    """簡易地表抽出: pixel ごとの min-Z 点だけ残す.      → この関数の説明メモ。
    本来は CSF (Cloth Simulation Filter) を使うが,      →   CSF = 布を上空から落として地面に張り付かせるアルゴリズム。
    ここではセル毎 min-Z で代用."""                      →   ここでは簡易版としてセルごとの最低点を使う。

    logger.info("Classify ground (min-Z per %.2fm cell)", cell_size)
                                                         → 「地面抽出開始。〇〇mセル」とログに記録する。

    xyz = pc.xyz                                         → 座標配列を xyz という短い変数名で扱えるようにする。

    ix = np.floor(xyz[:, 0] / cell_size).astype(np.int64)
                                                         → X座標をセルサイズで割って切り捨て → X方向のマス番号。
    iy = np.floor(xyz[:, 1] / cell_size).astype(np.int64)
                                                         → Y座標をセルサイズで割って切り捨て → Y方向のマス番号。

    key = ix * 73856093 ^ iy * 19349663                 → X・Yのマス番号を1つの整数キーに変換する（ハッシュ）。
                                                         →   同じマスに属する点は同じキーになる。

    order = np.argsort(key)                              → キーを小さい順に並べたときのインデックスを取得する。
    ks = key[order]                                      → キーを並べ替えた配列。
    zs = xyz[order, 2]                                   → Z座標もキーと同じ順番で並べ替えた配列。
    idxs = order                                         → 元の点番号の対応表（並べ替え後→元の番号）。

    u, first = np.unique(ks, return_index=True)         → 重複なしのキー一覧と、それぞれの最初の位置を取得する。

    # min-Z per cell: argmin via reduceat-like
    counts = np.diff(np.append(first, len(ks)))         → 各マスに何点入っているか数える。

    keep = np.zeros(len(xyz), dtype=bool)               → 全点を False（除去）で初期化した配列を作る。

    for k in range(len(u)):                             → 各マスについてループする。
        s, n = first[k], counts[k]                      →   s = そのマスの開始位置、n = そのマスの点数。
        local = zs[s:s+n]                               →   そのマスに含まれる点のZ座標だけ取り出す。
        keep[idxs[s + int(np.argmin(local))]] = True    →   Z座標が最小（最も低い）点だけ True にする。
                                                         →   argmin = 最小値の位置（インデックス）を返す関数。
                                                         →   idxs で元の点番号に変換してから True を立てる。

    n_in = int(keep.sum())                               → True の数（残る点の数）を数える。
    logger.info("  %d / %d ground points",              → 「〇〇点中〇〇点が地面点」とログに記録する。
                n_in, len(xyz))

    return PointCloud(xyz=pc.xyz[keep],                  → True の点だけ残した新しい PointCloud を返す。
        classification=pc.classification[keep] \        →   分類番号も同じ条件でフィルタリングする。
            if pc.classification is not None else None,
        intensity=pc.intensity[keep] \                  →   反射強度も同じ条件でフィルタリングする。
            if pc.intensity is not None else None,
        crs_epsg=pc.crs_epsg, extras=pc.extras)         →   座標系と追加データはそのまま引き継ぐ。


----------------------------------------------------------------
【preprocess 関数】　前処理をまとめて順番に実行するパイプライン
----------------------------------------------------------------

def preprocess(pc: PointCloud, cfg: dict,               → 前処理パイプラインを実行する関数。
               target_epsg: int | None = None) -> PointCloud:
                                                         →   cfg         = 設定を入れた辞書（何を実行するか指定）。
                                                         →   target_epsg = 変換先の座標系番号（省略可）。
    """前処理パイプラインを config に従って適用."""      → この関数の説明メモ。

    if target_epsg is not None and \                     → 変換先EPSG番号が指定されていて、
       pc.crs_epsg is not None:                         →   かつ元データに座標系情報がある場合のみ。
        pc = reproject(pc, target_epsg)                  →   座標系を変換する（reproject 関数を呼ぶ）。

    bbox = cfg.get("bbox")                               → 設定辞書から "bbox"（切り取り範囲）の値を取り出す。
                                                         →   get() は辞書にキーがなければ None を返す。
    if bbox:                                             → bbox が設定されている（None でない）場合。
        pc = clip_bbox(pc, bbox)                         →   範囲外の点を削除する（clip_bbox 関数を呼ぶ）。

    sor_cfg = cfg.get("sor", {})                        → 設定から "sor"（ノイズ除去）の設定を取り出す。
                                                         →   設定がなければ空の辞書 {} を使う。
    if sor_cfg.get("enabled"):                           → "enabled" が True に設定されている場合のみ実行。
        pc = sor_filter(pc,                              →   ノイズ除去を実行する（sor_filter 関数を呼ぶ）。
            k=sor_cfg.get("k", 16),                     →   k の値を設定から取得。なければデフォルト16。
            z_thresh=sor_cfg.get("z", 2.0))             →   z の値を設定から取得。なければデフォルト2.0。

    voxel = cfg.get("voxel_size")                       → 設定から "voxel_size"（ボクセルサイズ）を取り出す。
    if voxel:                                            → voxel_size が設定されている場合のみ実行。
        pc = voxel_downsample(pc, voxel)                →   点を間引く（voxel_downsample 関数を呼ぶ）。

    gf = cfg.get("ground_filter", {})                   → 設定から "ground_filter"（地面抽出）の設定を取り出す。
    if gf.get("enabled"):                               → "enabled" が True に設定されている場合のみ実行。
        pc = classify_ground(pc,                         →   地面の点だけ抽出する（classify_ground 関数を呼ぶ）。
            cell_size=gf.get("cell_size", 1.0))         →   cell_size を設定から取得。なければデフォルト1.0m。

    return pc                                            → 全ての前処理が終わったデータを返す。


================================================================
  全体の処理の流れ（まとめ）
================================================================

  [入力: PointCloud]
        ↓
  reproject()         座標系の変換　　　　　　　 ※target_epsg が指定された場合のみ
        ↓
  clip_bbox()         範囲外の点を削除　　　　　 ※cfg に bbox が設定された場合のみ
        ↓
  sor_filter()        ノイズ点を除去　　　　　　 ※cfg の sor.enabled が True の場合のみ
        ↓
  voxel_downsample()  点を間引いてデータ削減　　 ※cfg に voxel_size が設定された場合のみ
        ↓
  classify_ground()   地面の点だけ残す　　　　　 ※cfg の ground_filter.enabled が True の場合のみ
        ↓
  [出力: 処理済み PointCloud]

  ※ 各処理は設定（cfg）に基づいてスキップ可能。
     必要な処理だけを組み合わせて使える。

================================================================
