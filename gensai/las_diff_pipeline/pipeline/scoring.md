# ================================================================
damage_scoring.py　コード解説（コード ｜ 解説 の対応形式）

# 左側がコード、右側（→以降）がその解説です。

---

## 【ファイル冒頭・インポート】

"""Damage scoring."""                      → このファイルの説明メモ（被害のスコアリング処理）。

from **future** import annotations           → 型ヒントの書き方を新しいスタイルに統一するおまじない。

import logging                               → 動作記録（ログ）を残すための道具箱を読み込む。

import numpy as np                           → 大量の数値を高速に計算するライブラリを「np」という名前で読み込む。

logger = logging.getLogger(**name**)         → このファイル専用のログ出力係を作る。

---

## 【score_by_thresholds 関数】　数値をしきい値で区切ってスコア化する

def score_by_thresholds(values, thresholds):
→ 値のリストを「しきい値（区切り）」でグループ分けしてスコアにする関数。
"""|values| を thresholds でビン分けして 0..len(thresholds) に変換."""
→ 関数の説明メモ。
abs_v = np.abs(values)                   → 入力された値をすべて絶対値（プラスの値）に変換する。
score = np.zeros_like(abs_v, dtype=np.int8)
→ 計算結果を入れるための、中身が全部「0」の配列を準備する。
for t in thresholds:                     → しきい値を1つずつ取り出してループ処理する。
score = score + (abs_v >= t).astype(np.int8)
→ しきい値以上の場所は「1」を足す（超えるたびにスコアが上がる）。
return score                             → 最終的なスコア配列を返す。

---

## 【apply_significance 関数】　誤差レベルの小さな変化を無視する（0にする）

def apply_significance(dz, lod95, score):
→ 変化量(dz)、誤差限界(lod95)、現在のスコアを受け取って調整する関数。
"""M3C2 LoD95 で非有意点のスコアを 0 にする."""   → 関数の説明メモ。誤差と呼べるレベルのデータを無効化する。

```
if lod95 is None:                        → 誤差限界（LoD95）が設定されていない場合。
    sig = np.ones_like(dz, dtype=bool)   → すべての点を「意味のある変化（True）」として扱う。
    return score, sig                    → スコアはそのまま、判定結果と一緒に返す。

sig = np.abs(dz) > lod95                 → 変化の絶対値が、誤差限界（lod95）を超えているか判定する（True/False）。
score_adj = np.where(sig, score, 0).astype(np.int8)
                                         → np.where = 条件（sig）がTrueなら元のスコア、Falseなら「0」にする。
logger.info("Significance: %d / %d (%.1f%%) significant",
            int(sig.sum()), len(sig), 100.0 * sig.sum() / len(sig))
                                         → 全体のうち、何点（何％）が有意な変化だったかをログに記録する。
return score_adj, sig                    → 調整済みのスコアと、判定結果（True/False）を返す。

```

---

## 【building_score_from_stats 関数】　統計データから建物の被害スコア（0〜3）を決める

def building_score_from_stats(stats, rules):
→ 建物ごとの集計データ（stats）と判定ルール（rules）からスコアを決める関数。
"""建物単位の集計値から 0..3 のスコアを決定.""" → 関数の説明メモ。

```
dz_mean = stats.get("dz_mean")           → 建物エリア内の「平均の高さ変化量」を取得。
dz_p95 = stats.get("dz_p95")             → 建物エリア内の「上層95%タイルの高さ変化量」を取得。
loss_ratio = float(stats.get("loss_ratio", 0.0) or 0.0)
                                         → 点群がどれくらい消えたかの割合（消失率）。なければ 0.0。
n_pre = int(stats.get("n_points_pre", 0) or 0)
                                         → 災害前の建物の点数（ポイント数）。なければ 0。
n_post = int(stats.get("n_points_post", 0) or 0)
                                         → 災害後の建物の点数（ポイント数）。なければ 0。

thresholds = rules.get("thresholds", [0.3, 1.0, 3.0])
                                         → スコアを区切る高さを取得（デフォルトは 0.3m, 1.0m, 3.0m）。
min_pre = int(rules.get("min_pre_points", 30))
                                         → 判定に必要最低限な「災害前の点数」（デフォルトは30点）。
collapse_th = float(rules.get("loss_ratio_collapse", 0.6))
                                         → 倒壊とみなす消失率の基準（デフォルトは 60%）。
loss_min_dz = float(rules.get("loss_ratio_min_dz", 1.5))
                                         → 消失率で判定する際に、最低限必要な高さ変化（デフォルトは 1.5m）。

if n_pre >= min_pre and n_post == 0:     → 元々ちゃんと点があったのに、災害後に0点になった場合。
    return 3                             → 「完全消失」とみなして、即座に最高スコアの「3」を返す。

if dz_mean is not None and np.isfinite(dz_mean):
                                         → 平均変化量（dz_mean）がちゃんと計算できている（エラー値でない）場合。
    base = int(score_by_thresholds(np.array([dz_mean]), thresholds)[0])
                                         → 平均変化量をしきい値と照らし合わせて、ベースとなるスコア（0〜3）を決める。
elif dz_p95 is not None and np.isfinite(dz_p95):
                                         → 平均がダメで、95%値（dz_p95）が計算できている場合（バックアップ処理）。
    base = int(score_by_thresholds(np.array([dz_p95]), thresholds)[0])
                                         → 95%値をしきい値と照らし合わせて、ベーススコアを決める。
else:                                    → どちらのデータもない場合。
    base = 0                             → ベーススコアを「0」にする。

if (loss_ratio >= collapse_th and n_pre >= min_pre
        and dz_mean is not None and np.isfinite(dz_mean)
        and abs(dz_mean) >= loss_min_dz):
                                         → 「消失率が60%以上」かつ「十分な元の点数があり」かつ
                                         → 「平均変化量が1.5m以上」という厳しい条件（誤判定ガード）を満たした場合。
    base = max(base, 3)                  → 建物が潰れていると判断し、ベーススコアを「3」に引き上げる。

return int(min(base, 3))                 → スコアが3を超えないように制限（念のため）して、整数で返す。

```

# ================================================================
全体の処理の流れ（まとめ）

[建物ごとの統計データ (stats) と 判定ルール (rules) の入力]
↓

1. データの確認と準備
・災害前後の点数、高さの変化量（平均値など）、点群の消失率を読み出す。
↓
2. パターンA: 「完全消失」の判定
・災害前に点があったのに、災害後は「0」なら、その時点でスコア【3】で終了。
↓
3. パターンB: 「高さの変化」による基本スコア決定
・高さの変化量（dz_mean など）を `score_by_thresholds` にかける。
・しきい値（0.3m, 1.0m, 3.0m など）をいくつ超えたかで基本スコア【0 〜 3】を決める。
↓
4. パターンC: 「消失率（データの欠損）」による底上げ
・建物がペシャンコになり点群が大幅に消えた場合（消失率大、かつ高さ変化も一定以上）、
基本スコアが低くてもスコア【3】（倒壊）に引き上げる。
↓
5. スコア決定
・最終的に【0、1、2、3】のいずれかの被害レベルが確定して返される。

================================================================
