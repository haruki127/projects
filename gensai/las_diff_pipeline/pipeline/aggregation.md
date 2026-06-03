# aggregation.py コード1文ずつ解説

このファイルは、点群データの変化量 `dz` を、**グリッド単位**または**建物ポリゴン単位**で集計し、被害スコアを付与するためのコードです。

大きく分けると、次の3つの処理があります。

1. `aggregate_grid`：地図を正方形のグリッドに分けて、各セルごとに変化量を集計する。
2. `load_buildings`：建物ポリゴンをファイルまたはOpenStreetMapから読み込む。
3. `aggregate_buildings`：建物ごとに点群の変化量や点の減少率を集計し、被害スコアを付ける。

---

## 0. ファイル冒頭・import部分

### 1行目

```python
"""Aggregation: grid or building polygon."""
```

このファイル全体の説明です。

`Aggregation` は「集計」という意味です。ここでは、点群データをそのまま扱うのではなく、グリッドや建物ポリゴンごとにまとめる処理を行います。

発表では、次のように説明できます。

> このファイルは、点群データをグリッド単位または建物ポリゴン単位で集計する処理をまとめたものです。

---

### 3行目

```python
from __future__ import annotations
```

Pythonの将来バージョンの機能を先取りして使うための記述です。

ここでは主に、型ヒントに関する処理をより柔軟にするために使われます。今回のコードを理解するうえでは深く意識しなくて大丈夫です。

発表では、次のように説明できます。

> これは型ヒントを扱いやすくするための互換性用の記述です。処理の本体には直接関係しません。

---

### 5行目

```python
import logging
```

ログを出すための標準ライブラリを読み込んでいます。

ログとは、プログラムの実行中に「何件処理したか」「どこまで進んだか」などを記録する仕組みです。

このファイルでは、最後に「グリッドを何セル集計したか」「建物を何件読み込んだか」などを出力するために使われます。

---

### 6行目

```python
from pathlib import Path
```

ファイルパスを扱うための `Path` を読み込んでいます。

ただし、この `aggregation.py` の中では `Path` は実際には使われていません。別の処理で使う予定だったものが残っている可能性があります。

発表では、次のように説明できます。

> `Path` はファイルパスを扱うための機能ですが、このファイル内では使われていません。

---

### 8行目

```python
import numpy as np
```

数値計算ライブラリの NumPy を `np` という名前で読み込んでいます。

このコードでは、座標の配列処理、平均値、95パーセンタイル、欠損値の除外などに使われています。

発表では、次のように説明できます。

> NumPyは、点群の座標や変化量を配列として高速に計算するために使っています。

---

### 10行目

```python
from .scoring import score_by_thresholds, building_score_from_stats
```

同じパッケージ内の `scoring.py` から、スコア計算用の関数を読み込んでいます。

- `score_by_thresholds`：しきい値に基づいてグリッドの被害スコアを計算する関数です。
- `building_score_from_stats`：建物ごとの統計量から被害スコアを計算する関数です。

このファイルでは集計を行い、スコア判定の詳しい処理は別ファイルに任せています。

---

### 12行目

```python
logger = logging.getLogger(__name__)
```

このファイル専用のログ出力用オブジェクトを作っています。

`__name__` には、このファイルがどのモジュールとして読み込まれているかが入ります。これにより、どのファイルから出たログなのかを識別しやすくなります。

---

## 1. グリッド集計部分

### 15〜17行目

```python
# ───────────────────────────────────────
# GRID aggregation
# ───────────────────────────────────────
```

ここからグリッド集計に関する処理が始まることを示すコメントです。

処理には影響しませんが、コードを読む人が構造を理解しやすくなります。

---

### 18〜19行目

```python
def aggregate_grid(xyz, dz, cell_size, bbox=None, significant=None,
                    min_points: int = 10, thresholds=None):
```

`aggregate_grid` という関数を定義しています。

この関数は、点群データを一定サイズの正方形グリッドに分けて、各グリッド内の変化量 `dz` を集計し、被害スコアを付ける関数です。

引数の意味は次の通りです。

| 引数 | 意味 |
|---|---|
| `xyz` | 点群の座標データです。各点が x, y, z の値を持つ配列です。 |
| `dz` | 各点の変化量です。高さの差分などを表します。 |
| `cell_size` | グリッド1マスの大きさです。 |
| `bbox` | 集計範囲です。指定しない場合は点群全体から自動計算します。 |
| `significant` | 各点の変化が有意かどうかを表す配列です。 |
| `min_points` | 1つのグリッドに必要な最低点数です。デフォルトは10点です。 |
| `thresholds` | 被害スコアを判定するためのしきい値です。 |

発表では、次のように説明できます。

> `aggregate_grid` は、点群を正方形のグリッドに区切り、各セルごとに変化量の平均や95パーセンタイルを計算して、被害スコアを付ける関数です。

---

### 20行目

```python
    try:
```

ここから、エラーが起きる可能性のある処理を試します。

この後の `geopandas` や `shapely` の読み込みでエラーが起きた場合、`except` 側で分かりやすいエラーメッセージを出します。

---

### 21行目

```python
        import geopandas as gpd
```

地理空間データを扱うための `geopandas` を読み込んでいます。

`gpd` という名前で使えるようにしています。

この関数では、最後にグリッドごとの結果を `GeoDataFrame` として返すために使います。

---

### 22行目

```python
        from shapely.geometry import box
```

`shapely` から `box` を読み込んでいます。

`box` は、指定した座標から四角形のポリゴンを作る関数です。

このコードでは、グリッド1マス1マスを四角形ポリゴンとして作るために使います。

---

### 23行目

```python
    except ImportError as e:
```

`try` の中でライブラリの読み込みに失敗した場合、この処理に入ります。

`ImportError` は、必要なライブラリがインストールされていないときに起きるエラーです。

---

### 24行目

```python
        raise ImportError("geopandas/shapely required") from e
```

`geopandas` または `shapely` が必要であることを示すエラーを出します。

`from e` によって、元のエラー情報も保持します。

発表では、次のように説明できます。

> グリッドを地図上のポリゴンとして扱うため、geopandasとshapelyが必要です。入っていない場合はここでエラーになります。

---

### 26行目

```python
    thresholds = thresholds or [0.3, 1.0, 3.0]
```

被害スコア判定用のしきい値を設定しています。

`thresholds` が指定されていればその値を使います。指定されていなければ、デフォルトで `[0.3, 1.0, 3.0]` を使います。

この書き方は、次の意味です。

```python
if thresholds is None:
    thresholds = [0.3, 1.0, 3.0]
```

発表では、次のように説明できます。

> しきい値が指定されていない場合は、0.3、1.0、3.0を基準として被害スコアを計算します。

---

### 27行目

```python
    x, y = xyz[:, 0], xyz[:, 1]
```

点群データ `xyz` から、x座標とy座標だけを取り出しています。

`xyz[:, 0]` はすべての点のx座標、`xyz[:, 1]` はすべての点のy座標です。

ここではグリッドの位置を決めるために、平面上の座標である x と y を使っています。

---

### 28行目

```python
    if bbox is None:
```

集計範囲 `bbox` が指定されていないかを確認しています。

`bbox` は、`minx, miny, maxx, maxy` のように、処理対象の範囲を表す値です。

---

### 29行目

```python
        minx, miny, maxx, maxy = float(x.min()), float(y.min()), float(x.max()), float(y.max())
```

`bbox` が指定されていない場合、点群全体の最小・最大座標から集計範囲を自動で決めています。

- `x.min()`：x座標の最小値
- `y.min()`：y座標の最小値
- `x.max()`：x座標の最大値
- `y.max()`：y座標の最大値

`float()` を使って、NumPyの数値型ではなく通常のPythonの浮動小数点数に変換しています。

---

### 30行目

```python
    else:
```

`bbox` が指定されている場合はこちらに進みます。

---

### 31行目

```python
        minx, miny, maxx, maxy = bbox
```

指定された `bbox` をそのまま使って、集計範囲を設定しています。

---

### 32行目

```python
    nx = int(np.ceil((maxx - minx) / cell_size))
```

x方向に必要なグリッドの数を計算しています。

`maxx - minx` でx方向の範囲の長さを求め、それを `cell_size` で割ることで、何個のセルが必要かを計算します。

`np.ceil` は小数を切り上げる関数です。範囲がセルサイズで割り切れない場合でも、最後まで覆えるように切り上げています。

---

### 33行目

```python
    ny = int(np.ceil((maxy - miny) / cell_size))
```

y方向に必要なグリッドの数を計算しています。

考え方はx方向と同じです。

---

### 34行目

```python
    if nx <= 0 or ny <= 0:
```

グリッド数が正しいかを確認しています。

x方向またはy方向のグリッド数が0以下なら、範囲やセルサイズが不正です。

---

### 35行目

```python
        raise ValueError("Invalid bbox / cell_size")
```

範囲やセルサイズが不正な場合にエラーを出します。

例えば、`cell_size` が大きすぎる、0である、または `bbox` の最大値と最小値が逆になっている場合などが考えられます。

---

### 37行目

```python
    ix = np.floor((x - minx) / cell_size).astype(np.int64)
```

各点がx方向で何番目のグリッドに入るかを計算しています。

`x - minx` で左端からの距離を求め、それを `cell_size` で割ることで、セル番号を求めます。

`np.floor` は小数を切り捨てます。最後に `astype(np.int64)` で整数に変換しています。

---

### 38行目

```python
    iy = np.floor((y - miny) / cell_size).astype(np.int64)
```

各点がy方向で何番目のグリッドに入るかを計算しています。

考え方はx方向の `ix` と同じです。

---

### 39行目

```python
    valid = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & np.isfinite(dz)
```

有効な点だけを選ぶための条件を作っています。

条件は次の5つです。

1. `ix >= 0`：x方向のセル番号が0以上である。
2. `ix < nx`：x方向のセル番号が最大セル数より小さい。
3. `iy >= 0`：y方向のセル番号が0以上である。
4. `iy < ny`：y方向のセル番号が最大セル数より小さい。
5. `np.isfinite(dz)`：`dz` が有効な数値である。

`np.isfinite(dz)` により、`NaN` や無限大を除外しています。

---

### 40行目

```python
    ix, iy, dz_v = ix[valid], iy[valid], dz[valid]
```

有効な点だけを残しています。

`valid` が `True` の点について、x方向セル番号、y方向セル番号、変化量 `dz` を取り出しています。

ここで作られる `dz_v` は、有効な点だけの `dz` です。

---

### 41行目

```python
    sig_v = significant[valid] if significant is not None else None
```

`significant` が指定されている場合、有効な点だけに絞ります。

`significant` が指定されていない場合は `None` にします。

`significant` は、各点の変化が統計的に意味のある変化かどうかを表していると考えられます。

---

### 43行目

```python
    flat = iy * nx + ix
```

2次元のセル番号 `(ix, iy)` を、1次元のセル番号に変換しています。

たとえば横に `nx` 個のセルがあるとき、`iy * nx + ix` とすることで、すべてのセルに一意の番号を付けることができます。

この後、セルごとに点をまとめるために使います。

---

### 44行目

```python
    order = np.argsort(flat)
```

セル番号 `flat` を小さい順に並べるための並び替え順を取得しています。

`np.argsort` は、値そのものを並べ替えるのではなく、「どの順番に並べればよいか」というインデックスを返します。

---

### 45行目

```python
    flat_s = flat[order]; dz_s = dz_v[order]
```

セル番号と `dz` を、セル番号順に並び替えています。

セミコロン `;` により、1行に2つの文を書いています。

- `flat_s = flat[order]`：セル番号を並び替えます。
- `dz_s = dz_v[order]`：`dz` も同じ順番で並び替えます。

これにより、同じセルに属する点が連続して並ぶようになります。

---

### 46行目

```python
    sig_s = sig_v[order] if sig_v is not None else None
```

`significant` がある場合、それもセル番号順に並び替えます。

ない場合は `None` のままにします。

---

### 48行目

```python
    unique, first = np.unique(flat_s, return_index=True)
```

存在するセル番号と、そのセル番号が最初に現れる位置を取得しています。

- `unique`：点が存在するセル番号の一覧です。
- `first`：各セル番号が `flat_s` の中で最初に出てくる位置です。

`return_index=True` を指定することで、最初に出てくる位置も一緒に取得しています。

---

### 49行目

```python
    counts = np.diff(np.append(first, len(flat_s)))
```

各セルに含まれる点数を計算しています。

`first` には各セルの開始位置が入っています。そこに全体の長さ `len(flat_s)` を追加し、隣同士の差を取ることで、それぞれのセルに何点あるかが分かります。

---

### 51行目

```python
    records = []
```

集計結果を保存するための空のリストを作っています。

各グリッドセルの結果を辞書としてこのリストに追加していきます。

---

### 52行目

```python
    for k, key in enumerate(unique):
```

点が存在する各グリッドセルについて、1つずつ処理します。

- `k`：何番目のセルかを表すインデックスです。
- `key`：実際のセル番号です。

---

### 53行目

```python
        n = int(counts[k])
```

現在のグリッドセルに含まれる点数を取得しています。

`counts[k]` を `int` に変換して、Pythonの整数として扱えるようにしています。

---

### 54行目

```python
        if n < min_points:
```

そのセルに含まれる点数が、最低点数 `min_points` より少ないかを確認しています。

点数が少なすぎると統計量の信頼性が低くなるためです。

---

### 55行目

```python
            continue
```

点数が少なすぎるセルは処理をスキップします。

`continue` は、現在のループ処理を飛ばして、次のセルに進む命令です。

---

### 56行目

```python
        seg = slice(first[k], first[k] + n)
```

現在のセルに対応するデータ範囲を作っています。

`first[k]` がそのセルの開始位置で、`first[k] + n` が終了位置です。

`slice` を使うことで、そのセルに含まれる点だけをまとめて取り出せます。

---

### 57行目

```python
        dz_seg = dz_s[seg]
```

現在のセルに含まれる `dz` だけを取り出しています。

`dz_seg` は、そのグリッドセル内の変化量の集まりです。

---

### 58行目

```python
        dz_mean = float(np.mean(dz_seg))
```

そのセル内の `dz` の平均値を計算しています。

これは、そのグリッド内で平均的にどれくらい変化したかを表します。

---

### 59行目

```python
        dz_p95 = float(np.percentile(np.abs(dz_seg), 95))
```

そのセル内の `dz` の絶対値について、95パーセンタイルを計算しています。

`np.abs(dz_seg)` によって、正負に関係なく変化の大きさだけを見ています。

95パーセンタイルとは、値を小さい順に並べたとき、下から95%の位置にある値です。極端な外れ値の影響を少し抑えつつ、大きな変化を反映できます。

発表では、次のように説明できます。

> 平均値だけでは局所的な大きな変化が埋もれる可能性があるため、95パーセンタイルを使って大きめの変化も評価しています。

---

### 60行目

```python
        sig_ratio = float(np.mean(sig_s[seg])) if sig_s is not None else 1.0
```

そのセル内で、有意な変化と判定された点の割合を計算しています。

`sig_s` がある場合は、その平均を取ります。`True` は1、`False` は0として扱われるため、平均を取ると割合になります。

`sig_s` がない場合は、すべて有意とみなして `1.0` にしています。

---

### 62行目

```python
        cy = key // nx; cx = key % nx
```

1次元のセル番号 `key` を、y方向とx方向のセル番号に戻しています。

セミコロンで2つの文が1行に書かれています。

- `cy = key // nx`：y方向のセル番号です。
- `cx = key % nx`：x方向のセル番号です。

`//` は割り算の商、`%` は余りを求めます。

---

### 63行目

```python
        x0 = minx + cx * cell_size
```

現在のセルの左下のx座標を計算しています。

全体の左端 `minx` に、x方向セル番号 `cx` とセルサイズの積を足しています。

---

### 64行目

```python
        y0 = miny + cy * cell_size
```

現在のセルの左下のy座標を計算しています。

全体の下端 `miny` に、y方向セル番号 `cy` とセルサイズの積を足しています。

---

### 65行目

```python
        geom = box(x0, y0, x0 + cell_size, y0 + cell_size)
```

現在のグリッドセルを四角形ポリゴンとして作成しています。

`box(左下x, 左下y, 右上x, 右上y)` の形で指定します。

この `geom` が、地図上に表示できる1つのグリッドセルになります。

---

### 67行目

```python
        score = int(score_by_thresholds(np.array([dz_p95]), thresholds)[0])
```

`dz_p95` としきい値 `thresholds` を使って、被害スコアを計算しています。

`score_by_thresholds` は配列を受け取る関数なので、`np.array([dz_p95])` のように1要素の配列にしています。

戻り値も配列なので、`[0]` で最初のスコアを取り出し、`int()` で整数に変換しています。

---

### 68行目

```python
        if sig_ratio < 0.5:
```

有意な変化の割合が50%未満かどうかを確認しています。

有意な点が少ない場合、変化の信頼性が低いと判断します。

---

### 69行目

```python
            score = max(score - 1, 0)
```

有意な変化の割合が低い場合、被害スコアを1段階下げています。

ただし、`max(score - 1, 0)` としているため、スコアが0未満になることはありません。

発表では、次のように説明できます。

> 変化量が大きくても、有意な点の割合が少ない場合は信頼性が低いため、スコアを1段階下げています。

---

### 71行目

```python
        records.append({
```

現在のグリッドセルの集計結果を、`records` リストに追加し始めています。

辞書形式で、セルの形状やスコア、統計量を保存します。

---

### 72行目

```python
            "geometry": geom, "id": f"g_{int(key):07d}",
```

出力する情報として、グリッドの形状とIDを設定しています。

- `geometry`：グリッドセルの四角形ポリゴンです。
- `id`：グリッドセルのIDです。

`f"g_{int(key):07d}"` は、例えば `g_0000123` のように、7桁の番号付きIDを作る書き方です。

---

### 73行目

```python
            "damage_score": score,
```

被害スコアを保存しています。

---

### 74行目

```python
            "dz_mean": round(dz_mean, 3), "dz_p95": round(dz_p95, 3),
```

`dz` の平均値と95パーセンタイルを保存しています。

`round(..., 3)` により、小数第3位までに丸めています。

---

### 75行目

```python
            "n_points": n, "significant_ratio": round(sig_ratio, 3),
```

そのセルに含まれる点数と、有意な変化の割合を保存しています。

有意な変化の割合も小数第3位までに丸めています。

---

### 76行目

```python
            "method": "grid",
```

この結果がグリッド集計によるものだと分かるように、`method` に `"grid"` を保存しています。

---

### 77行目

```python
        })
```

1つのグリッドセルについての辞書を閉じ、`records` への追加を完了しています。

---

### 79行目

```python
    gdf = gpd.GeoDataFrame(records, geometry="geometry")
```

集計結果のリスト `records` を、`GeoDataFrame` に変換しています。

`GeoDataFrame` は、表形式のデータに地理情報を持たせたものです。

ここでは `geometry` 列を地理形状として指定しています。

---

### 80行目

```python
    logger.info("Grid aggregation: %d cells", len(gdf))
```

グリッド集計の結果、何個のセルが作られたかをログに出力しています。

`%d` には `len(gdf)`、つまり集計されたセル数が入ります。

---

### 81行目

```python
    return gdf
```

グリッドごとの集計結果を返しています。

返される `gdf` には、各グリッドの形状、被害スコア、点数、統計量などが含まれます。

---

## 2. 建物ポリゴン読み込み部分

### 84〜86行目

```python
# ───────────────────────────────────────
# BUILDING polygons
# ───────────────────────────────────────
```

ここから建物ポリゴンに関する処理が始まることを示すコメントです。

---

### 87行目

```python
def load_buildings(cfg: dict, work_epsg: int):
```

`load_buildings` という関数を定義しています。

この関数は、建物ポリゴンを読み込むための関数です。

引数の意味は次の通りです。

| 引数 | 意味 |
|---|---|
| `cfg` | 建物データの読み込み方法を指定する設定辞書です。 |
| `work_epsg` | 作業用の座標系を表すEPSGコードです。 |

---

### 88行目

```python
    """建物ポリゴンを取得 (file or osm)."""
```

この関数の説明です。

建物ポリゴンを、ファイルまたはOpenStreetMapから取得するという意味です。

---

### 89行目

```python
    try:
```

ここから、エラーが起きる可能性のある処理を試します。

具体的には、`geopandas` の読み込みを試しています。

---

### 90行目

```python
        import geopandas as gpd
```

建物ポリゴンの読み込みや座標変換を行うために、`geopandas` を読み込んでいます。

---

### 91行目

```python
    except ImportError as e:
```

`geopandas` がインストールされていない場合、この処理に入ります。

---

### 92行目

```python
        raise ImportError("geopandas required") from e
```

`geopandas` が必要であることを示すエラーを出します。

---

### 94行目

```python
    source = cfg.get("source", "file")
```

建物データの取得元を設定から読み取っています。

`cfg` の中に `source` があればその値を使います。なければデフォルトで `"file"` を使います。

つまり、特に指定しない場合はファイルから建物データを読み込む設定になります。

---

### 95行目

```python
    if source == "file":
```

建物データの取得元がファイルかどうかを判定しています。

---

### 96行目

```python
        path = cfg.get("file")
```

設定辞書 `cfg` から、建物データのファイルパスを取得しています。

---

### 97行目

```python
        if not path:
```

ファイルパスが指定されていないかを確認しています。

`path` が空文字、`None` などの場合に、この条件が真になります。

---

### 98行目

```python
            raise ValueError("aggregation.building.file is required when source='file'")
```

ファイルから読み込む設定なのにファイルパスが指定されていない場合、エラーを出します。

---

### 99行目

```python
        gdf = gpd.read_file(path)
```

指定されたファイルから建物ポリゴンを読み込んでいます。

`gpd.read_file` は、Shapefile、GeoJSON、GeoPackageなどの地理空間ファイルを読み込むための関数です。

読み込まれた建物データは `gdf` に入ります。

---

### 100行目

```python
    elif source == "osm":
```

建物データの取得元がOpenStreetMapかどうかを判定しています。

`source` が `"file"` ではなく `"osm"` の場合、こちらの処理に入ります。

---

### 101行目

```python
        try:
```

OpenStreetMapからデータを取得するために必要なライブラリを読み込む処理を試します。

---

### 102行目

```python
            import osmnx as ox
```

OpenStreetMapから地理データを取得するための `osmnx` を読み込んでいます。

`ox` という名前で使えるようにしています。

---

### 103行目

```python
        except ImportError as e:
```

`osmnx` がインストールされていない場合、この処理に入ります。

---

### 104行目

```python
            raise ImportError("osmnx required for source='osm'") from e
```

OSMから建物を取得するには `osmnx` が必要であることを示すエラーを出します。

---

### 105行目

```python
        bbox = cfg.get("bbox")
```

OSMから取得する範囲を、設定辞書 `cfg` から取得しています。

`bbox` は、`minx, miny, maxx, maxy` の形で範囲を表します。

---

### 106行目

```python
        if bbox is None:
```

OSMから取得する範囲が指定されていないかを確認しています。

---

### 107行目

```python
            raise ValueError("aggregation.building.bbox is required when source='osm'")
```

OSMから取得する場合に `bbox` がないと、どの範囲の建物を取得すればよいか分かりません。そのためエラーを出します。

---

### 108行目

```python
        from pyproj import Transformer
```

座標系を変換するための `Transformer` を読み込んでいます。

OSMは緯度経度の座標系を使うため、作業用の座標系から緯度経度に変換する必要があります。

---

### 109行目

```python
        tr = Transformer.from_crs(work_epsg, 4326, always_xy=True)
```

座標変換器を作っています。

`work_epsg` から `4326` に変換する設定です。

EPSG:4326 は、緯度経度を表す一般的な座標系です。

`always_xy=True` は、座標の順番を常に x, y、つまり経度、緯度の順に扱うための指定です。

---

### 110行目

```python
        minx, miny, maxx, maxy = bbox
```

指定された範囲 `bbox` を、4つの値に分けています。

---

### 111行目

```python
        lon_min, lat_min = tr.transform(minx, miny)
```

範囲の左下座標を、作業用座標系から緯度経度に変換しています。

`lon_min` は最小経度、`lat_min` は最小緯度です。

---

### 112行目

```python
        lon_max, lat_max = tr.transform(maxx, maxy)
```

範囲の右上座標を、作業用座標系から緯度経度に変換しています。

`lon_max` は最大経度、`lat_max` は最大緯度です。

---

### 113行目

```python
        gdf = ox.features.features_from_bbox(
```

OpenStreetMapから、指定範囲内の地物を取得する処理を始めています。

取得結果は `gdf` に入ります。

---

### 114行目

```python
            north=lat_max, south=lat_min, east=lon_max, west=lon_min,
```

OSMから取得する範囲を指定しています。

- `north`：北端の緯度
- `south`：南端の緯度
- `east`：東端の経度
- `west`：西端の経度

---

### 115行目

```python
            tags={"building": True},
```

OpenStreetMapの中から、`building` タグが付いた地物だけを取得する指定です。

つまり、建物として登録されているデータを取得します。

---

### 116行目

```python
        )
```

`features_from_bbox` の呼び出しを閉じています。

---

### 117行目

```python
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
```

取得したOSMデータの中から、形状がポリゴンのものだけを残しています。

建物は面として扱いたいので、`Polygon` または `MultiPolygon` のみを対象にします。

点や線のデータはここで除外されます。

---

### 118行目

```python
    else:
```

`source` が `"file"` でも `"osm"` でもない場合の処理です。

---

### 119行目

```python
        raise ValueError(f"Unknown building source: {source}")
```

未知の建物データ取得元が指定された場合にエラーを出します。

`f"...{source}"` により、実際に指定された値をエラーメッセージに含めています。

---

### 121行目

```python
    if gdf.crs is None:
```

読み込んだ建物データに座標系情報があるかを確認しています。

`crs` は Coordinate Reference System の略で、座標系を意味します。

---

### 122行目

```python
        logger.warning("Buildings have no CRS; assuming EPSG:4326")
```

建物データに座標系が設定されていない場合、警告ログを出します。

ここでは、座標系がないためEPSG:4326だと仮定する、という内容をログに残しています。

---

### 123行目

```python
        gdf = gdf.set_crs(epsg=4326)
```

座標系が設定されていない建物データに、EPSG:4326を設定しています。

注意点として、これは座標を変換しているのではなく、「このデータはEPSG:4326です」とラベルを付けている処理です。

---

### 124行目

```python
    gdf = gdf.to_crs(epsg=work_epsg)
```

建物データを作業用の座標系 `work_epsg` に変換しています。

点群データと建物ポリゴンの座標系が違うと、正しく重ね合わせできません。そのため、ここで座標系を統一しています。

---

### 125行目

```python
    logger.info("Loaded %d buildings", len(gdf))
```

読み込んだ建物の数をログに出力しています。

`len(gdf)` が建物数です。

---

### 126行目

```python
    return gdf
```

読み込み・座標変換が完了した建物ポリゴンの `GeoDataFrame` を返しています。

---

## 3. 建物単位の集計部分

### 129〜130行目

```python
def aggregate_buildings(xyz_pre, xyz_post, dz, buildings_gdf, rules,
                         buffer: float = 0.5, significant=None):
```

`aggregate_buildings` という関数を定義しています。

この関数は、建物ポリゴンごとに、点群の変化量や点の減少率を集計し、被害スコアを付ける関数です。

引数の意味は次の通りです。

| 引数 | 意味 |
|---|---|
| `xyz_pre` | 変化前の点群座標です。 |
| `xyz_post` | 変化後の点群座標です。 |
| `dz` | 変化後の各点に対応する変化量です。 |
| `buildings_gdf` | 建物ポリゴンのGeoDataFrameです。 |
| `rules` | 建物スコアを決めるためのルールです。 |
| `buffer` | 建物ポリゴンを外側に少し広げる距離です。デフォルトは0.5です。 |
| `significant` | 各点の変化が有意かどうかを表す配列です。 |

発表では、次のように説明できます。

> `aggregate_buildings` は、建物ごとに変化前後の点数、点の喪失率、dzの統計量を計算し、それらをもとに建物単位の被害スコアを付ける関数です。

---

### 131行目

```python
    """建物ポリゴン毎に dz / 点喪失率を集計しスコア付与 (sjoin ベース)."""
```

この関数の説明です。

建物ポリゴンごとに、`dz` と点喪失率を集計し、スコアを付けるという意味です。

`sjoin` は spatial join の略で、空間結合を意味します。点がどの建物の中にあるかを判定する処理です。

---

### 132行目

```python
    try:
```

ここから、`geopandas` の読み込みを試します。

---

### 133行目

```python
        import geopandas as gpd
```

地理空間データを扱うために `geopandas` を読み込んでいます。

この関数では、点群を点の地理データに変換したり、建物ポリゴンとの空間結合を行ったりします。

---

### 134行目

```python
    except ImportError as e:
```

`geopandas` がインストールされていない場合、この処理に入ります。

---

### 135行目

```python
        raise ImportError("geopandas required") from e
```

`geopandas` が必要であることを示すエラーを出します。

---

### 137行目

```python
    bgdf = buildings_gdf.reset_index(drop=True).copy()
```

建物データをコピーしています。

`reset_index(drop=True)` によって、インデックスを0から振り直します。

`copy()` によって、元の `buildings_gdf` を直接変更しないようにしています。

---

### 138行目

```python
    bgdf["_bidx"] = bgdf.index.astype(np.int64)
```

建物ごとに `_bidx` という番号を付けています。

`bgdf.index` は建物のインデックスで、それを整数型に変換して `_bidx` 列に保存しています。

この番号は、点がどの建物に入っているかを判定した後の集計に使います。

---

### 139行目

```python
    if buffer and buffer > 0:
```

建物ポリゴンを広げる処理を行うかどうかを判定しています。

`buffer` が指定されていて、かつ0より大きい場合だけ処理します。

---

### 140行目

```python
        bgdf["geometry"] = bgdf.geometry.buffer(buffer)
```

建物ポリゴンを外側に `buffer` 分だけ広げています。

デフォルトでは `buffer=0.5` なので、建物の周囲を0.5m広げます。

点群と建物ポリゴンには少しずれがある場合があるため、建物内の点を拾いやすくする目的があります。

---

### 141行目

```python
    crs = bgdf.crs
```

建物データの座標系を取得しています。

この後に作る点群のGeoDataFrameにも同じ座標系を設定します。

---

### 143行目

```python
    pre_pts = gpd.GeoDataFrame(
```

変化前の点群を、地理情報を持つ `GeoDataFrame` として作成し始めています。

---

### 144行目

```python
        {"_pi": np.arange(len(xyz_pre), dtype=np.int64)},
```

変化前の各点に `_pi` という点番号を付けています。

`np.arange(len(xyz_pre))` は、0から点数-1までの連番を作ります。

---

### 145行目

```python
        geometry=gpd.points_from_xy(xyz_pre[:, 0], xyz_pre[:, 1]),
```

変化前の点群のx座標とy座標から、点のジオメトリを作っています。

`gpd.points_from_xy` は、x座標とy座標の配列から、地図上の点データを作る関数です。

---

### 146行目

```python
        crs=crs,
```

変化前点群の座標系として、建物データと同じ座標系を指定しています。

---

### 147行目

```python
    )
```

変化前点群の `GeoDataFrame` 作成を完了しています。

---

### 148行目

```python
    sig_arr = significant if significant is not None else np.ones(len(dz), dtype=bool)
```

有意な変化を表す配列を準備しています。

`significant` が指定されていればそれを使います。

指定されていない場合は、`np.ones(len(dz), dtype=bool)` により、すべて `True` の配列を作ります。

つまり、有意性情報がない場合は、すべての点を有意な変化として扱います。

---

### 149行目

```python
    post_pts = gpd.GeoDataFrame(
```

変化後の点群を、地理情報を持つ `GeoDataFrame` として作成し始めています。

---

### 150行目

```python
        {"_pi": np.arange(len(xyz_post), dtype=np.int64),
```

変化後の各点に `_pi` という点番号を付けています。

`np.arange(len(xyz_post))` により、0から点数-1までの連番を作っています。

---

### 151行目

```python
         "_dz": dz.astype(np.float64),
```

変化後の各点に対応する `dz` を `_dz` という列に保存しています。

`astype(np.float64)` により、64ビット浮動小数点数に変換しています。

---

### 152行目

```python
         "_sig": sig_arr.astype(np.float64)},
```

有意な変化かどうかを表す値を `_sig` という列に保存しています。

`True` / `False` の値を `float64` に変換しているため、`True` は1.0、`False` は0.0として扱われます。

この後、平均を取ることで有意な点の割合を計算できます。

---

### 153行目

```python
        geometry=gpd.points_from_xy(xyz_post[:, 0], xyz_post[:, 1]),
```

変化後の点群のx座標とy座標から、点のジオメトリを作っています。

---

### 154行目

```python
        crs=crs,
```

変化後点群の座標系として、建物データと同じ座標系を指定しています。

---

### 155行目

```python
    )
```

変化後点群の `GeoDataFrame` 作成を完了しています。

---

### 157行目

```python
    pre_join = gpd.sjoin(pre_pts, bgdf[["_bidx", "geometry"]], predicate="within", how="inner")
```

変化前の点群と建物ポリゴンを空間結合しています。

`predicate="within"` は、点が建物ポリゴンの中にある場合に結合するという意味です。

`how="inner"` は、建物内に入った点だけを残すという意味です。

これにより、各点がどの建物に属するかを判定できます。

---

### 158行目

```python
    post_join = gpd.sjoin(post_pts, bgdf[["_bidx", "geometry"]], predicate="within", how="inner")
```

変化後の点群と建物ポリゴンを空間結合しています。

変化前と同様に、建物内にある点だけを取り出し、その点がどの建物に入っているかを判定します。

---

### 159行目

```python
    pre_counts = pre_join.groupby("_bidx").size().to_dict()
```

変化前の点について、建物ごとに点数を数えています。

`groupby("_bidx")` で建物番号ごとにグループ化し、`size()` で点数を数えます。

最後に `to_dict()` で辞書に変換しています。

例えば、次のような形になります。

```python
{0: 120, 1: 85, 2: 40}
```

これは、建物0に120点、建物1に85点、建物2に40点あるという意味です。

---

### 161行目

```python
    records = []
```

建物ごとの集計結果を保存するための空のリストを作っています。

---

### 162行目

```python
    for bi, geom in enumerate(bgdf.geometry):
```

建物ポリゴンを1つずつ処理します。

- `bi`：建物番号です。
- `geom`：その建物の形状です。

---

### 163行目

```python
        post_in = post_join[post_join["_bidx"] == bi] if len(post_join) else post_join.iloc[:0]
```

現在の建物 `bi` の中にある、変化後の点だけを取り出しています。

`len(post_join)` が0でなければ、`_bidx` が現在の建物番号と一致する点を抽出します。

もし `post_join` が空の場合は、`post_join.iloc[:0]` により空のデータフレームを作ります。

---

### 164行目

```python
        n_post = int(len(post_in))
```

現在の建物内にある変化後の点数を数えています。

---

### 165行目

```python
        n_pre = int(pre_counts.get(bi, 0))
```

現在の建物内にあった変化前の点数を取得しています。

`pre_counts.get(bi, 0)` は、建物番号 `bi` の点数が辞書にあればそれを返し、なければ0を返します。

---

### 166行目

```python
        if n_pre == 0 and n_post == 0:
```

変化前も変化後も点がない建物かどうかを確認しています。

---

### 167行目

```python
            continue
```

変化前も変化後も点がない建物は、集計できないためスキップします。

---

### 169行目

```python
        if n_post > 0:
```

変化後の点が1点以上あるかどうかを確認しています。

変化後の点がある場合は、`dz` の平均や95パーセンタイルを計算できます。

---

### 170行目

```python
            dz_seg = post_in["_dz"].to_numpy()
```

現在の建物内にある変化後の点から、`dz` の値だけを取り出しています。

`to_numpy()` により、NumPy配列に変換しています。

---

### 171行目

```python
            dz_seg = dz_seg[np.isfinite(dz_seg)]
```

`dz_seg` から、有効な数値だけを残しています。

`np.isfinite` により、`NaN` や無限大を除外しています。

---

### 172行目

```python
            dz_mean = float(np.mean(dz_seg)) if len(dz_seg) else float("nan")
```

建物内の `dz` の平均値を計算しています。

有効な `dz` が1つ以上あれば平均を計算します。なければ `nan` にします。

`nan` は Not a Number の略で、計算できない値を表します。

---

### 173行目

```python
            dz_p95 = float(np.percentile(np.abs(dz_seg), 95)) if len(dz_seg) else float("nan")
```

建物内の `dz` の絶対値について、95パーセンタイルを計算しています。

有効な `dz` がない場合は `nan` にします。

---

### 174行目

```python
            sig_ratio = float(post_in["_sig"].mean()) if significant is not None else 1.0
```

建物内で有意な変化と判定された点の割合を計算しています。

`significant` が指定されている場合は、`_sig` の平均を取ります。

指定されていない場合は、すべて有意とみなして `1.0` にします。

---

### 175行目

```python
        else:
```

変化後の点が1点もない場合の処理です。

---

### 176行目

```python
            dz_mean = float("nan"); dz_p95 = float("nan"); sig_ratio = 0.0
```

変化後の点がないため、`dz` の平均値や95パーセンタイルは計算できません。

そのため、`dz_mean` と `dz_p95` には `nan` を入れています。

有意な変化の割合 `sig_ratio` は0.0にしています。

セミコロンで3つの文が1行に書かれています。

---

### 178行目

```python
        loss_ratio = 1.0 - (n_post / n_pre) if n_pre > 0 else 0.0
```

点喪失率を計算しています。

点喪失率は、変化前の点数に対して、変化後の点数がどれだけ減ったかを表します。

式は次の通りです。

```python
loss_ratio = 1 - 変化後の点数 / 変化前の点数
```

例えば、変化前に100点あり、変化後に60点であれば、

```python
1 - 60 / 100 = 0.4
```

となり、40%の点が失われたと考えます。

`n_pre` が0の場合は計算できないため、0.0にしています。

---

### 179行目

```python
        loss_ratio = max(0.0, min(1.0, loss_ratio))
```

点喪失率を0.0から1.0の範囲に収めています。

変化後の点数が変化前より多い場合、`loss_ratio` がマイナスになる可能性があります。その場合は0.0にします。

逆に1.0を超える場合は1.0にします。

---

### 181行目

```python
        stats = {
```

被害スコア計算に使う統計情報を辞書として作り始めています。

---

### 182行目

```python
            "loss_ratio": loss_ratio,
```

点喪失率を `stats` に保存しています。

---

### 183行目

```python
            "dz_mean": dz_mean, "dz_p95": dz_p95,
```

`dz` の平均値と95パーセンタイルを `stats` に保存しています。

---

### 184行目

```python
            "n_points_pre": n_pre, "n_points_post": n_post,
```

変化前と変化後の点数を `stats` に保存しています。

---

### 185行目

```python
        }
```

統計情報の辞書 `stats` を閉じています。

---

### 186行目

```python
        merged_rules = dict(rules)
```

スコア判定ルール `rules` をコピーしています。

元の `rules` を直接変更しないようにするためです。

---

### 187行目

```python
        merged_rules.setdefault("thresholds", [0.3, 1.0, 3.0])
```

スコア判定ルールの中に `thresholds` がなければ、デフォルト値 `[0.3, 1.0, 3.0]` を設定します。

`setdefault` は、指定したキーが存在しない場合だけ値を追加するメソッドです。

---

### 188行目

```python
        score = building_score_from_stats(stats, merged_rules)
```

建物ごとの統計量 `stats` とルール `merged_rules` を使って、被害スコアを計算しています。

この計算の詳細は、別ファイルの `building_score_from_stats` 関数に任されています。

---

### 190行目

```python
        records.append({
```

現在の建物の集計結果を `records` リストに追加し始めています。

---

### 191行目

```python
            "geometry": geom, "id": f"b_{bi:07d}",
```

建物の形状とIDを保存しています。

- `geometry`：建物ポリゴンです。
- `id`：建物IDです。

`f"b_{bi:07d}"` により、例えば `b_0000001` のようなIDを作ります。

---

### 192行目

```python
            "damage_score": score,
```

建物の被害スコアを保存しています。

---

### 193行目

```python
            "dz_mean": None if not np.isfinite(dz_mean) else round(dz_mean, 3),
```

`dz_mean` を保存しています。

ただし、`dz_mean` が `nan` や無限大の場合は、`None` に変換しています。

有効な数値であれば、小数第3位まで丸めて保存します。

---

### 194行目

```python
            "dz_p95": None if not np.isfinite(dz_p95) else round(dz_p95, 3),
```

`dz_p95` を保存しています。

`dz_p95` が有効な数値でない場合は `None` にし、有効な数値であれば小数第3位まで丸めます。

---

### 195行目

```python
            "n_points_pre": n_pre, "n_points_post": n_post,
```

変化前と変化後の点数を保存しています。

---

### 196行目

```python
            "loss_ratio": round(loss_ratio, 3),
```

点喪失率を小数第3位まで丸めて保存しています。

---

### 197行目

```python
            "significant_ratio": round(sig_ratio, 3),
```

有意な変化の割合を小数第3位まで丸めて保存しています。

---

### 198行目

```python
            "method": "building",
```

この結果が建物単位の集計であることを示すために、`method` に `"building"` を保存しています。

---

### 199行目

```python
        })
```

1つの建物についての集計結果の辞書を閉じ、`records` に追加する処理を完了しています。

---

### 201行目

```python
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=buildings_gdf.crs)
```

建物ごとの集計結果を `GeoDataFrame` に変換しています。

`geometry="geometry"` により、`geometry` 列を地理形状として指定しています。

`crs=buildings_gdf.crs` により、元の建物データと同じ座標系を設定しています。

---

### 202行目

```python
    logger.info("Building aggregation: %d buildings scored", len(gdf))
```

スコアが付けられた建物数をログに出力しています。

`len(gdf)` が、集計結果として残った建物数です。

---

### 203行目

```python
    return gdf
```

建物ごとの集計結果を返しています。

返される `gdf` には、建物形状、被害スコア、変化量、点数、点喪失率などが含まれています。

---

## 4. 全体の流れまとめ

この `aggregation.py` の全体の流れは次の通りです。

1. 点群データと変化量 `dz` を受け取る。
2. グリッド単位で見る場合は、対象範囲を正方形セルに分ける。
3. 各セル内の `dz_mean` や `dz_p95` を計算する。
4. 建物単位で見る場合は、建物ポリゴンを読み込む。
5. 点群と建物ポリゴンを空間結合し、どの点がどの建物に入るかを判定する。
6. 建物ごとに、変化前後の点数、点喪失率、`dz` の統計量を計算する。
7. `scoring.py` の関数を使って、被害スコアを付ける。
8. 結果を `GeoDataFrame` として返す。

---

## 5. 発表用の短い説明

発表では、次のようにまとめると分かりやすいです。

> このファイルは、点群データの変化量を空間単位で集計するためのものです。集計方法は2つあり、1つ目は地図を一定サイズの正方形に分けるグリッド集計、2つ目は建物ポリゴンごとに集計する建物集計です。グリッド集計では、各セルに含まれる点の変化量の平均や95パーセンタイルを計算し、しきい値に基づいて被害スコアを付けます。建物集計では、建物ポリゴンと点群を空間結合し、変化前後の点数や点喪失率、dzの統計量を使って建物ごとの被害スコアを算出します。最終的には、地図上で扱えるGeoDataFrameとして結果を返します。

---

## 6. 特に重要な用語

| 用語 | 意味 |
|---|---|
| `xyz` | 点群の座標データです。 |
| `dz` | 高さなどの変化量です。 |
| `cell_size` | グリッド1マスの大きさです。 |
| `bbox` | 処理対象の範囲です。 |
| `significant` | 変化が有意かどうかを表します。 |
| `dz_mean` | 変化量の平均です。 |
| `dz_p95` | 変化量の絶対値の95パーセンタイルです。 |
| `loss_ratio` | 変化前後で点がどれだけ減ったかを表す割合です。 |
| `GeoDataFrame` | 地理情報を持つ表データです。 |
| `sjoin` | 点とポリゴンを位置関係で結合する空間結合です。 |

