================================================================
  io_las.py　コード解説（コード ｜ 解説 の対応形式）
================================================================
左側がコード、右側（→以降）がその解説です。
================================================================


----------------------------------------------------------------
【ファイル冒頭・インポート】
----------------------------------------------------------------

"""Point cloud I/O — LAS / CSV."""          → このファイルの説明メモ。プログラムの動作には影響しない。

from __future__ import annotations           → 型ヒントの書き方を新しいスタイルに統一するおまじない。

import logging                               → ログ（動作記録）を残すための道具箱を読み込む。
from dataclasses import dataclass, field     → データをまとめる「箱」クラスを簡単に作る道具を読み込む。
from pathlib import Path                     → ファイルのパス（場所）を扱いやすくする道具を読み込む。
from typing import Optional                  → 「値がNone（空）になる場合もある」と示すメモ用の道具を読み込む。

import numpy as np                           → 大量の数値を高速に計算するライブラリを「np」という名前で読み込む。

logger = logging.getLogger(__name__)         → このファイル専用のログ出力係を作る。


----------------------------------------------------------------
【PointCloud クラス】　点群データをまとめる「箱」の設計図
----------------------------------------------------------------

@dataclass                                   → 「データ管理クラスを簡単に作る」モードにする特別な印。
class PointCloud:                            → PointCloud という名前のクラス（設計図）を定義する。

    xyz: np.ndarray                          → 全点のXYZ座標を入れる配列。(N行3列)の表形式。
                                             →   N = 点の総数、3列 = X・Y・Z それぞれの値。
    classification: Optional[np.ndarray] = None
                                             → 各点の分類番号（地面・建物・植物など）。なければNone。
    intensity: Optional[np.ndarray] = None   → 各点の反射強度（レーザーの跳ね返りの強さ）。なければNone。
    crs_epsg: Optional[int] = None           → 座標系のEPSG番号（地図の座標ルール）。なければNone。
    extras: dict = field(default_factory=dict)
                                             → その他の追加データを自由に入れられる辞書。
                                             →   field(default_factory=dict) は「デフォルト値を空の辞書{}にする」意味。

    @property                                → 次のメソッドを「変数のように呼べる」関数にする印。
    def n(self) -> int:                      → 点の総数を返す機能。pc.n のように変数と同じ書き方で使える。
        return len(self.xyz)                 → xyz の行数（点の数）を返す。


----------------------------------------------------------------
【read_las 関数】　LAS / LAZ ファイルを読み込む
----------------------------------------------------------------

def read_las(path: str | Path) -> PointCloud:
                                             → LASファイルを読み込む関数。パスを受け取りPointCloudを返す。
    """LAS / LAZ を読む."""                  → この関数の説明メモ。

    try:                                     → ここからエラーが起きるかもしれない処理を試みる。
        import laspy                         → LASファイルを扱うライブラリを読み込む。
    except ImportError as e:                 → laspyがインストールされていなかった場合の処理。
        raise ImportError("laspy is required to read LAS") from e
                                             → わかりやすいメッセージのエラーを出して終了する。

    path = Path(path)                        → 文字列でもPathオブジェクトでも扱えるようにPathに統一する。
    logger.info("Reading LAS: %s", path)    → 「このファイルを読み込みます」とログに記録する。
    las = laspy.read(str(path))             → laspyでLASファイルを読み込む。

    xyz = np.column_stack([                  → X・Y・Z 座標を3列横に並べて1つの配列にまとめる。
        np.asarray(las.x, dtype=np.float64),→   X座標を高精度小数（float64）の配列に変換。
        np.asarray(las.y, dtype=np.float64),→   Y座標を高精度小数（float64）の配列に変換。
        np.asarray(las.z, dtype=np.float64) →   Z座標を高精度小数（float64）の配列に変換。
    ])

    cls = np.asarray(las.classification, dtype=np.int8) if hasattr(las, "classification") else None
                                             → 分類番号を取り出す。データがなければNoneにする。
                                             →   hasattr =「この属性が存在するか？」を確認する関数。
                                             →   dtype=np.int8 = 小さな整数型として格納。

    inten = np.asarray(las.intensity, dtype=np.uint16) if hasattr(las, "intensity") else None
                                             → 反射強度を取り出す。データがなければNoneにする。
                                             →   dtype=np.uint16 = 符号なし16ビット整数として格納。

    epsg = None                              → EPSG番号の初期値はNone（情報がない状態）にしておく。
    try:                                     → ここからエラーが起きても止まらないように試みる。
        crs = las.header.parse_crs()        → ファイルのヘッダー（先頭情報）から座標系を解析する。
        if crs is not None:                 → 座標系情報が存在する場合だけ次の処理をする。
            auth = crs.to_authority()       → 座標系の識別情報（種類と番号）を取り出す。
            if auth and auth[0] == "EPSG":  → EPSG形式の座標系であるか確認する。
                epsg = int(auth[1])         → EPSG番号を整数として取り出す。
    except Exception:                       → 何らかのエラーが起きた場合。
        pass                                → 何もせず無視して続ける（情報がなくても問題ない）。

    return PointCloud(xyz=xyz, classification=cls, intensity=inten, crs_epsg=epsg)
                                             → 読み込んだデータをPointCloudにまとめて返す。


----------------------------------------------------------------
【read_csv 関数】　CSV ファイルを読み込む
----------------------------------------------------------------

def read_csv(path: str | Path, fallback_epsg: int | None = None) -> PointCloud:
                                             → CSVファイルを読み込む関数。
                                             →   fallback_epsg = ファイルにEPSG情報がない場合の代替番号。
    """CSV (x,y,z header 必須) を読む."""   → この関数の説明メモ。

    path = Path(path)                        → パスをPathオブジェクトに統一する。
    logger.info("Reading CSV: %s", path)    → 「このCSVを読み込みます」とログに記録する。
    arr = np.genfromtxt(str(path), delimiter=",", names=True)
                                             → NumPyでCSVファイルを読み込む。
                                             →   delimiter="," = カンマ区切りで読む。
                                             →   names=True    = 1行目を列名として扱う（x,y,z が必須）。

    xyz = np.column_stack([arr["x"], arr["y"], arr["z"]]).astype(np.float64)
                                             → "x" "y" "z" 列を取り出して横に並べ、高精度小数に変換する。

    return PointCloud(xyz=xyz, crs_epsg=fallback_epsg)
                                             → PointCloudにまとめて返す。
                                             →   CSVにはEPSG情報がないので引数の値をそのまま使う。


----------------------------------------------------------------
【read_auto 関数】　拡張子で自動判別して読み込む
----------------------------------------------------------------

def read_auto(path: str | Path, fallback_epsg: int | None = None) -> PointCloud:
                                             → 拡張子を見てLASかCSVを自動で選んで読み込む関数。
    """拡張子で振り分け."""                  → この関数の説明メモ。

    path = Path(path)                        → パスをPathオブジェクトに統一する。
    ext = path.suffix.lower()               → 拡張子を取得して小文字に統一する（.LAS と .las を同じ扱いにする）。

    if ext in (".las", ".laz"):             → 拡張子が .las または .laz の場合。
        pc = read_las(path)                  →   read_las でLASファイルを読み込む。
        if pc.crs_epsg is None and fallback_epsg is not None:
                                             →   EPSG番号がなく、代替番号が指定されている場合。
            pc.crs_epsg = fallback_epsg     →     代替EPSG番号を上書きする。
        return pc                            →   PointCloudを返す。

    if ext == ".csv":                        → 拡張子が .csv の場合。
        return read_csv(path, fallback_epsg=fallback_epsg)
                                             →   read_csv でCSVファイルを読み込んで返す。

    raise ValueError(f"Unsupported file type: {ext}")
                                             → 対応していない拡張子の場合はエラーを出して終了する。
                                             →   f"...{ext}" = f文字列。{}の中に変数を埋め込める書き方。


----------------------------------------------------------------
【write_las 関数】　LAS ファイルに書き出す
----------------------------------------------------------------

def write_las(pc: PointCloud, path: str | Path, extra_dims: dict | None = None) -> None:
                                             → PointCloudをLASファイルに書き出す関数。
                                             →   extra_dims = 追加で保存したいデータ（省略可）。
                                             →   -> None = 戻り値なし（ファイル保存だけが目的）。
    """LAS で書き出す.                       → この関数の説明メモ（複数行）。
    extra_dims: {name: ndarray} で追加属性を保存可能."""

    try:                                     → laspyが使えるか試みる。
        import laspy
    except ImportError as e:
        raise ImportError("laspy is required to write LAS") from e
                                             → インストールされていなければエラーを出して終了する。

    path = Path(path)                        → パスをPathオブジェクトに統一する。
    path.parent.mkdir(parents=True, exist_ok=True)
                                             → 保存先フォルダがなければ自動で作成する。
                                             →   parents=True  = 途中のフォルダも全部作る。
                                             →   exist_ok=True = すでにあってもエラーにしない。

    header = laspy.LasHeader(point_format=3, version="1.4")
                                             → LASファイルのヘッダー（先頭情報）を作る。
                                             →   point_format=3  = データの格納形式の番号。
                                             →   version="1.4"   = LAS規格のバージョン。

    if pc.n > 0:                             → 点が1つ以上ある場合。
        header.offsets = pc.xyz.min(axis=0) →   座標の基準点を全点の最小値に設定する。
                                             →   min(axis=0) = 列ごと（X・Y・Z それぞれ）の最小値を取る。
    else:                                    → 点が0個の場合。
        header.offsets = np.array([0.0, 0.0, 0.0])
                                             →   基準点を [0, 0, 0] にする。
    header.scales = np.array([0.001, 0.001, 0.001])
                                             → 座標の精度を0.001m（1mm単位）に設定する。

    if pc.crs_epsg is not None:             → EPSG番号がある場合。
        try:
            import pyproj                    →   座標系ライブラリを読み込む。
            header.add_crs(pyproj.CRS.from_epsg(pc.crs_epsg))
                                             →   EPSG番号から座標系情報を作ってヘッダーに記録する。
        except Exception:
            pass                             →   エラーが起きても無視して続ける。

    if extra_dims:                           → 追加データがある場合。
        for name, arr in extra_dims.items():→   辞書から名前と配列を1つずつ取り出してループする。
            header.add_extra_dim(laspy.ExtraBytesParams(name=name, type=np.float32))
                                             →   その追加データをヘッダーに登録する。

    las = laspy.LasData(header)             → ヘッダーを使って書き出し用のオブジェクトを作る。

    if pc.n > 0:                             → 点が1つ以上ある場合のみデータを書き込む。
        las.x = pc.xyz[:, 0]                →   全点のX座標を書き込む（0列目）。
        las.y = pc.xyz[:, 1]                →   全点のY座標を書き込む（1列目）。
        las.z = pc.xyz[:, 2]                →   全点のZ座標を書き込む（2列目）。

        if pc.classification is not None:   →   分類番号があれば書き込む。
            las.classification = pc.classification
        if pc.intensity is not None:        →   反射強度があれば書き込む。
            las.intensity = pc.intensity

        if extra_dims:                       →   追加データがある場合。
            for name, arr in extra_dims.items():
                                             →     名前と配列を1つずつ取り出してループする。
                setattr(las, name, np.asarray(arr, dtype=np.float32))
                                             →     setattr = オブジェクトに動的に属性を追加する関数。
                                             →     las.name = 値 と書けない場合（名前が変数のとき）に使う。

    las.write(str(path))                    → ファイルに保存する。
    logger.info("Wrote LAS: %s (%d points)", path, pc.n)
                                             → 「保存完了・何点保存したか」をログに記録する。


================================================================
  全体の処理の流れ（まとめ）
================================================================

  [入力ファイル: .las / .laz / .csv]
        ↓
  read_auto()　　　拡張子を確認して振り分け
        ↓
  read_las() または read_csv()　　データを読み込む
        ↓
  PointCloud　　　xyz・分類・強度・EPSGをひとまとめに管理
        ↓
  （外部で前処理などを行う）
        ↓
  write_las()　　　ヘッダー作成 → データ書き込み → ファイル保存
        ↓
  [出力ファイル: .las]

================================================================
