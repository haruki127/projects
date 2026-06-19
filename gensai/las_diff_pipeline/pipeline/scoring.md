# `scoring.py` コード解説

このファイルは、点群の変化量（差分）や建物の統計データをもとに、被害の大きさ（被害スコア）を自動で判定・計算するためのコードです。

主な役割は次の3つです。

1. **しきい値による段階判定**: 変化量をあらかじめ決めたしきい値（例: 0.3m、1.0m、3.0m）と比較し、被害の段階（0〜3など）に変換する
2. **統計的有意性の判定**: 変化量が「誤差の範囲（LoD95）」に収まる小さなものである場合、それは「変化なし（スコア0）」として扱い、ノイズを除去する
3. **建物単位の総合被害判定**: 変化量だけでなく、被災前後の点数の減少率（消失率）なども組み合わせて、最終的な建物の被害スコア（0: 無被害 〜 3: 倒壊・消失）を判定する

---

## 全体像

```python
"""Damage scoring."""

```

このファイルの説明文です。意味は「被害スコアの計算」です。

発表では、次のように説明できます。

> このファイルは、計算された点群の変化量から、具体的にどれくらいの被害が出ているのかを数字のスコア（0〜3など）に変換するルールが書かれています。

---

## 1. しきい値によるスコアリング関数

```python
def score_by_thresholds(values, thresholds):
    """|values| を thresholds でビン分けして 0..len(thresholds) に変換."""
    abs_v = np.abs(values)
    score = np.zeros_like(abs_v, dtype=np.int8)
    for t in thresholds:
        score = score + (abs_v >= t).astype(np.int8)
    return score

```

この関数は、変化量の絶対値（`np.abs`）がしきい値をいくつ超えているかを数え、スコアを計算します。

例えば、しきい値（`thresholds`）が `[0.3, 1.0, 3.0]` の場合：

* 変化が `0.2m` の場合：どれも超えないので **スコア 0**
* 変化が `0.5m` の場合：`0.3` を超える（1つ）ので **スコア 1**
* 変化が `1.5m` の場合：`0.3` と `1.0` を超える（2つ）ので **スコア 2**
* 変化が `4.0m` の場合：すべてを超える（3つ）ので **スコア 3**

発表では、次のように説明できます。

> ここでは、変化量の絶対値が設定されたしきい値を何段階超えているかをチェックし、0から3までの段階的なスコアに分類しています。

---

## 2. 有意差によるスコア補正関数

```python
def apply_significance(dz, lod95, score):
    """M3C2 LoD95 で非有意点のスコアを 0 にする."""

```

計測データには必ずわずかな誤差が含まれます。この関数は、変化量（`dz`）が「誤差の限界値（`lod95`）」を超えているかどうか（有意な変化かどうか）を判定します。

```python
    if lod95 is None:
        sig = np.ones_like(dz, dtype=bool)
        return score, sig
    sig = np.abs(dz) > lod95
    score_adj = np.where(sig, score, 0).astype(np.int8)

```

もし変化量の絶対値が誤差限界 `lod95` より小さければ、それは「ただの計測誤差」とみなして、計算されたスコアを強制的に `0` に書き換えます（`np.where`）。

発表では、次のように説明できます。

> 計測誤差による誤判定を防ぐため、変化量が誤差の限界値より小さい場合は、変化がなかったものとしてスコアを `0` にリセットする処理を行っています。

---

## 3. 建物単位の被害判定関数

```python
def building_score_from_stats(stats, rules):
    """建物単位の集計値から 0..3 のスコアを決定."""

```

このファイルの最重要関数です。建物の様々な統計情報（`stats`）と、判定ルール（`rules`）を突き合わせて、その建物の最終的な被害スコア（最大3）を決定します。

### データの準備とデフォルト値の設定

```python
    dz_mean = stats.get("dz_mean")
    dz_p95 = stats.get("dz_p95")
    loss_ratio = float(stats.get("loss_ratio", 0.0) or 0.0)
    n_pre = int(stats.get("n_points_pre", 0) or 0)
    n_post = int(stats.get("n_points_post", 0) or 0)

    thresholds = rules.get("thresholds", [0.3, 1.0, 3.0])
    min_pre = int(rules.get("min_pre_points", 30))
    collapse_th = float(rules.get("loss_ratio_collapse", 0.6))
    loss_min_dz = float(rules.get("loss_ratio_min_dz", 1.5))

```

建物内の平均変化量（`dz_mean`）や、被災前の点数（`n_pre`）、被災後の点数（`n_post`）、点数の減少率（`loss_ratio`）などを取得します。

### 判定ルール1：完全消失のチェック

```python
    if n_pre >= min_pre and n_post == 0:
        return 3

```

被災前には十分な点数（例: 30点以上）があったにもかかわらず、被災後に点数が `0` になった場合は、建物が跡形もなく消え去った（**完全消失**）とみなして、即座に **スコア 3** を返します。

### 判定ルール2：変化量による基本スコアの計算

```python
    if dz_mean is not None and np.isfinite(dz_mean):
        base = int(score_by_thresholds(np.array([dz_mean]), thresholds)[0])
    elif dz_p95 is not None and np.isfinite(dz_p95):
        base = int(score_by_thresholds(np.array([dz_p95]), thresholds)[0])
    else:
        base = 0
    ...

```

完全消失ではない場合、建物の平均変化量（`dz_mean`）をもとに、先ほどのしきい値関数を使って基本スコアを計算します。平均値がない場合は、95パーセンタイル値（`dz_p95`）で代用します。

### 判定ルール3：点数減少（消失率）による底上げと暴走ガード

```python
    if (loss_ratio >= collapse_th and n_pre >= min_pre
            and dz_mean is not None and np.isfinite(dz_mean)
            and abs(dz_mean) >= loss_min_dz):
        base = max(base, 3)

    return int(min(base, 3))

```

建物の点数が設定（例: 60%）以上減っている（`loss_ratio >= collapse_th`）場合、建物が**倒壊**している可能性が高いため、スコアを **3に底上げ** します。

ただし、被災前のデータ（生のレーザ点群）と被災後のデータ（写真から作ったDSMなど）でデータの密度が大きく異なる場合、単にデータの性質の違いだけで「点数が減った」と誤判定される危険があります。そのため、「平均変化量も一定以上（例: 1.5m以上）大きいこと」という暴走防止ガード（安全装置）が仕込まれています。

発表では、次のように説明できます。

> 建物単位の被害判定では、まず「建物が完全に消えていないか」をチェックし、次に「平均で何メートル沈んだか（あるいは壊れたか）」で基本スコアを決めます。さらに、点数が急激に減っている場合は倒壊とみなしてスコアを引き上げますが、データの種類の違いによる誤判定を防ぐための安全ガードも組み込まれています。

---

# このファイル全体のまとめ

この `scoring.py` は、解析によって得られた「メートル単位の変化」という物理的な数値を、「被害の深刻度（スコア）」という実用的な情報に翻訳するコードです。

ただ機械的にしきい値で区切るだけでなく、計測誤差を無視するための「有意差判定（LoD95）」や、建物が完全に無くなった場合を捉える「完全消失判定」、そして異なるデータ源の組み合わせによる誤判定を防ぐ「暴走防止ガード」など、実際の災害解析で発生しやすいトラブルを想定した極めて実用的なロジックが組まれています。

---



---


