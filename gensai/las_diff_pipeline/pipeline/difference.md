# difference.py — 高さ変化の計算

災害前後の点群を比較し、「どこがどれだけ高さが変わったか」を計算するモジュール。主にDSM差分法を使い、オプションでM3C2法も呼べる。（後述の`pdal` のインストールとパイプラインJSONの実装が必要）

---

## 処理の流れ

```
PointCloud (pre)  ┐
                  ├─ rasterize_dsm() → DSM (pre_r)  ┐
PointCloud (post) ┘                                  ├─ post_r - pre_r → diff raster → write_geotiff()
                    rasterize_dsm() → DSM (post_r)  ┘
```

---

## `rasterize_dsm(xyz, resolution, bbox, method)`

バラバラな3D点群を、指定した解像度の格子状グリッド（DSM）に変換。→点群の密度が異なる問題はこれで解決。

### 引数

| 引数 | 型 | 内容 |
|---|---|---|
| `xyz` | `ndarray (N, 3)` | 点群のXYZ座標 |
| `resolution` | `float` | グリッドの1セルあたりの幅（メートル） |
| `bbox` | `tuple` | グリッドの範囲 `(minx, miny, maxx, maxy)` |
| `method` | `str` | セル内の集約方法（下表参照） |

### `method` の選択肢

| 値 | 内容 | 使いどころ |
|---|---|---|
| `max`（デフォルト） | セル内の最高点を採用 | 建物・地表の上面を捉える |
| `min` | セル内の最低点を採用 | 地盤沈下の検出 |
| `mean` | セル内の平均高さ | ノイズを平滑化したい場合 |

### 注意点
- 点が1つも存在しないセルは `NaN`（データなし）になる。
- Y軸は上下反転して出力されます（GIS慣例：上が北＝Y大）。

---

## `dsm_diff(pre, post, resolution=0.5, method="max")`

前後の点群を同じグリッド座標でDSM化し、セルごとに `post - pre` を計算する。

### 引数

| 引数 | 型 | 内容 |
|---|---|---|
| `pre` | `PointCloud` | 災害前の点群 |
| `post` | `PointCloud` | 災害後の点群 |
| `resolution` | `float` | グリッド解像度（デフォルト：0.5m） |
| `method` | `str` | DSMの集約方法（デフォルト：`max`） |

**戻り値**：`(diff_raster, bbox)` のタプル。そのまま `write_geotiff()` に渡せる。

### 差分値の解釈

```
正の値 → 高くなった（土砂堆積・瓦礫の積み上がりなど）
負の値 → 低くなった（建物崩壊・地盤沈下など）
NaN   → 前後どちらかのデータが欠損している箇所
```

**補足**：前後の点群の範囲が異なっていても、両者を包む共通のバウンディングボックスで統一するため、同じグリッド座標で差し引きできる。

---

## `write_geotiff(raster, bbox, path, epsg)`

差分ラスタを地理参照情報付きの**GeoTIFF**として書き出す。QGISやArcGISで直接開いて可視化できる。

### 引数

| 引数 | 型 | 内容 |
|---|---|---|
| `raster` | `ndarray` | 書き出す差分ラスタ |
| `bbox` | `tuple` | グリッドの地理範囲 `(minx, miny, maxx, maxy)` |
| `path` | `str / Path` | 出力先ファイルパス |
| `epsg` | `int` | 座標系のEPSGコード |

> **依存ライブラリ**：`rasterio` が必要。未インストールの場合は実行時エラーになる。

---

## `m3c2(pre, post, work_dir, ...)` ※未実装

DSM差分より精度の高い**M3C2法**（点群を直接比較する手法）の予約関数です。現在は `NotImplementedError` を投げる。

利用するには `pdal` のインストールとパイプラインJSONの実装が必要。**現時点では `method='dsm'` を使用する。**

---

## 依存ライブラリ

| ライブラリ | 用途 | 必須 / オプション |
|---|---|---|
| `numpy` | 点群の数値計算 | 必須 |
| `rasterio` | GeoTIFF書き出し | 必須（`write_geotiff`を使う場合） |
| `pdal` | M3C2法の実行 | オプション（未実装） |
