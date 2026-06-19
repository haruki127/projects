# `registration.py` コード解説

このファイルは、位置がズレている2つの点群データ（ソースとターゲット）の位置合わせ（レジストレーション）を行うためのコードです。

主な役割は次の3つです。

1. **ICP（Iterative Closest Point）アルゴリズム**を用いて、点群間の位置ズレを補正する変換行列を計算する
2. `stable_mask`（地殻変動などの影響を受けていない動かない領域）を指定することで、地すべりや建物の崩壊などの**変化に影響されない正確な位置合わせ**を行う
3. 推奨ライブラリ（Open3D）がインストールされていない環境でも、SciPyを用いた自前実装の計算へ自動で切り替える（フォールバック）仕組みを持つ

---

## 全体像

```python
"""ICP registration (Open3D primary, scipy fallback)."""

```

このファイルの説明文です。

意味は「ICPアルゴリズムによる位置合わせ（通常はOpen3Dを使用し、利用できない場合はSciPyで代用）」です。

発表では、次のように説明できます。

> このファイルは、2つの点群の位置をぴったり合わせるための処理が書かれています。基本的にはOpen3Dという高度なライブラリを使いますが、それが使えない環境でもSciPyを使って自動で計算をカバーする、タフな設計になっています。

---

## 1. 安定領域（マスク）の読み込み

```python
def _load_stable_mask(path):
    try:
        import geopandas as gpd
    except ImportError as e:
        raise ImportError("geopandas is required for stable_mask") from e
    return gpd.read_file(path)

```

この関数は、位置合わせの基準として使う「動いていない領域（ポリゴンデータ）」を読み込みます。

関数の中で `import geopandas` を行うことで、この機能（マスク処理）を使わない場合はGeopandasがインストールされていなくてもエラーにならないよう工夫されています。

発表では、次のように説明できます。

> ここでは、位置合わせの基準にするための「動かない領域」のデータを読み込んでいます。必要なときだけライブラリを読み込む工夫がされています。

---

## 2. ポリゴンによる点群のフィルタリング

```python
def _mask_points_in_polygons(xyz, gdf, epsg):

```

読み込んだ動かない領域（ポリゴン）の内側にある点群だけを抽出するための関数です。

### 座標系の統一と判定

```python
    if gdf.crs is None:
        logger.warning("stable_mask has no CRS; assuming EPSG:%d", epsg)
        gdf = gdf.set_crs(epsg=epsg)
    elif gdf.crs.to_epsg() != epsg:
        gdf = gdf.to_crs(epsg=epsg)

```

ポリゴンデータと点群データの座標系（EPSGコード）が一致しているかを確認し、ズレていればポリゴン側の座標系を点群に合わせます（`to_crs`）。

```python
    union = gdf.unary_union
    mask = np.array([union.contains(Point(p[0], p[1])) for p in xyz], dtype=bool)

```

複数のポリゴンを1つにまとめ（`unary_union`）、各点群のXY座標（`p[0], p[1]`）がその範囲内に「含まれているか（`contains`）」を判定して、真偽値のリスト（マスク）を作ります。

発表では、次のように説明できます。

> 点群データとポリゴンデータの座標系を正しく合わせたあと、指定した範囲の中に点群が含まれているかどうかを1点ずつ判定して、位置合わせに使う点を選別しています。

---

## 3. メイン処理：icp_align 関数

```python
def icp_align(source: PointCloud, target: PointCloud,
              stable_mask_path=None, max_iterations: int = 50, threshold: float = 0.5):

```

位置合わせを行うメインの関数です。動かす前の点群（`source`）を、基準となる点群（`target`）に合わせます。

### 事前チェックとマスクの適用

```python
    if source.crs_epsg != target.crs_epsg:
        raise ValueError("CRS must match before ICP")

```

2つの点群の座標系が異なる場合はエラーを出します。

```python
    if stable_mask_path is not None:
        ...
        src_xyz = source.xyz[m_src]
        tgt_xyz = target.xyz[m_tgt]
    else:
        logger.warning("stable_mask not provided. Using all points; displaced regions may bias.")
        src_xyz = source.xyz
        tgt_xyz = target.xyz

```

動かない領域（マスク）が指定されていればその中の点群だけを抽出し、指定がない場合はすべての点群を使います。ただし、警告にある通り、地形変化があった場所の点群まで位置合わせの計算に使うと、結果が歪む（バイアスがかかる）原因になります。

```python
    if len(src_xyz) < 100 or len(tgt_xyz) < 100:
        raise RuntimeError("Too few points for ICP")

```

計算に使う点数が少なすぎる（100点未満）場合は、正しく計算できないため処理を中断します。

発表では、次のように説明できます。

> 2つの点群の座標系が一致しているかチェックし、指定があれば動かない領域の点だけを抽出します。点数が少なすぎる場合はエラーを発生させて安全に処理を止めます。

---

## 4. ライブラリの有無に応じた処理の分岐（フォールバック）

```python
    try:
        import open3d  # noqa: F401
        T = _icp_open3d(src_xyz, tgt_xyz, max_iterations, threshold)
    except ImportError:
        logger.info("open3d not available; using scipy-based ICP fallback")
        T = _icp_scipy(src_xyz, tgt_xyz, max_iterations, threshold)

```

非常に重要なポイントです。

C++ベースで高速な `open3d` ライブラリの読み込みを試み、成功すればOpen3Dで高速に計算します。もし環境にOpen3Dがインストールされていなければ、標準的な `scipy` を使った自前実装の関数（`_icp_scipy`）へ自動的に切り替えます。

発表では、次のように説明できます。

> ここがこのコードの特徴で、高速な `open3d` ライブラリが使える環境ならそれを使い、使えない環境であれば自動的に `scipy` を使った計算に切り替えることで、どんな環境でも動作するようにしています。

---

## 5. 計算された変換行列の適用と出力

```python
    homo = np.column_stack([source.xyz, np.ones(source.n)])
    new_xyz = (homo @ T.T)[:, :3]
    aligned = PointCloud(xyz=new_xyz, classification=source.classification, ...)
    return aligned, T

```

計算によって得られた4×4の変換行列 `T`（回転と平行移動の情報）を、元のソース点群全体に適用（行列掛け算）します。これによって位置が補正された新しい点群オブジェクト（`aligned`）と、どれくらい動かしたかの情報（`T`）を一緒に返します。

発表では、次のように説明できます。

> 求まった変換行列を使って、元の点群データ全体の座標を動かします。最終的に、位置がぴったり合った新しい点群データと、変換に使った行列を返します。

---

## 6. Open3D による高速な ICP 処理

```python
def _icp_open3d(src_xyz, tgt_xyz, max_iter, threshold):

```

Open3Dライブラリを呼び出してICPアルゴリズムを実行する内部関数です。

```python
    result = o3d.pipelines.registration.registration_icp(
        src, tgt, max_correspondence_distance=threshold, init=np.eye(4),
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        criteria=o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=max_iter),
    )

```

点対点の距離（Point-to-Point）を最小化する手法で、指定された反復回数（`max_iter`）と、対応付ける点の最大距離（`threshold`）をもとに最適化を行います。

発表では、次のように説明できます。

> Open3Dの標準的なICP機能を使って、非常に高速かつ正確に位置合わせの計算を行っています。

---

## 7. SciPy による自前実装の ICP 処理（フォールバック用）

```python
def _icp_scipy(src_xyz, tgt_xyz, max_iter, threshold):

```

Open3Dが使えない場合の代替え関数です。「Umeyama法（SVD分解を用いた点群合わせ）」と呼ばれる有名なアルゴリズムを愚直にPython（NumPy/SciPy）で実装しています。

### ダウンサンプリング

```python
    max_pts = 200_000
    if len(src_xyz) > max_pts:
        idx = rs.choice(len(src_xyz), max_pts, replace=False)
        src = src_xyz[idx].astype(np.float64)

```

点群が多すぎると自前計算では非常に時間がかかるため、最大20万点にランダムサンプリングして計算を軽量化しています。

### 最近傍探索（cKDTree）

```python
    tree = cKDTree(tgt)
    ...
    d, idx = tree.query(cur, distance_upper_bound=threshold * 5.0)

```

ターゲット点群の「空間的な木構造（k-d木）」を作成し、現在のソース点群から一番近いターゲットの点を効率よく探します。

### SVD（特異値分解）による回転・移動の計算

```python
    U, _, Vt = np.linalg.svd((s - sm).T @ (t - tm))
    ...
    R = Vt.T @ D @ U.T
    tr = tm - R @ sm

```

最も近い点同士のペア（`s` と `t`）の中心を合わせ、特異値分解（SVD）を行うことで、誤差が最も少なくなる回転行列 `R` と平行移動ベクトル `tr` を数学的に導き出します。これを設定した回数、あるいは誤差（RMSE）が縮まらなくなるまで繰り返します。

発表では、次のように説明できます。

> Open3Dが使えない場合は、SciPyの `cKDTree` を使って最も近い点を探し、数学的な手法（SVD分解）を使って自前で回転と移動の計算を繰り返します。点数が多すぎる場合は自動で20万点に間引いて、処理が重くなりすぎないようにする工夫も入っています。

---

# このファイル全体のまとめ

この `registration.py` は、ズレている点群同士の位置を数学的にぴったり合わせるためのコードです。

ただ位置を合わせるだけでなく、地殻変動や建物変化に惑わされないように「動いていないことが確実なエリア（マスク領域）」の点だけで計算を行う仕組みを持っています。さらに、処理が強力な `Open3D` ライブラリだけでなく、一般的な `SciPy` による自前の数式実装も備えており、実行される環境を選ばずに安定して動作するように設計されています。

---

# 発表用の短い説明例

このファイルは、2つの点群の位置ズレを補正する「ICP位置合わせ」を行うコードです。特徴として、地すべりなどで変化した場所を計算から除外するために、あらかじめ指定した「動かない領域」の点だけを抽出して計算する工夫がされています。また、環境への配慮として、高性能な `Open3D` ライブラリがインストールされていればそれを使い、未導入であれば `SciPy` と数学的な計算（SVD分解）を用いた自前実装のアルゴリズムへ自動で切り替わる仕組みになっており、エラーで落ちにくい堅牢なシステムになっています。

