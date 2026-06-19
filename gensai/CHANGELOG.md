# CHANGELOG

---

## 2026-06-03 — バグ修正 5 件 (by Cowork / Claude)

### Bug 1 — `examples/run_realdata.py` : データパス修正

| | 内容 |
|---|---|
| **ファイル** | `examples/run_realdata.py` |
| **症状** | 実行すると即 `FileNotFoundError` |
| **原因** | PRE / POST のパスが移行前の場所（`D:\notowest14\`）を指していた |

```diff
- PRE  = r"D:\notowest14\07FD2032.las"
- POST = r"D:\ground_data_07fd1_2025\07fd203_grd.las"
+ PRE  = r"D:\projects\notowest14\07FD2032.las"
+ POST = r"D:\projects\ground_data_07fd1_2025\07fd203_grd.las"
```

---

### Bug 2 — `pipeline/preprocess.py` : ハッシュ衝突によるボクセル誤合算

| | 内容 |
|---|---|
| **ファイル** | `pipeline/preprocess.py` |
| **関数** | `voxel_downsample`, `classify_ground` |
| **症状** | 大規模データで統計値に微小な誤差、再現性のない挙動 |
| **原因** | XOR ベースのハッシュキーで異なるボクセルが同一キーに衝突し、無関係な点が同グループに混入していた |

**`voxel_downsample` の変更:**

```diff
- ix = np.floor(xyz / voxel_size).astype(np.int64)
- key = ix[:, 0].astype(np.int64) * 73856093 ^ ix[:, 1] * 19349663 ^ ix[:, 2] * 83492791
- order = np.argsort(key)
- ks = key[order]; xs = xyz[order]
- u, first = np.unique(ks, return_index=True)
- sums = np.add.reduceat(xs, first, axis=0)
- counts = np.diff(np.append(first, len(ks)))
- centroids = sums / counts[:, None]
+ ix = np.floor(xyz / voxel_size).astype(np.int64)
+ order = np.lexsort((ix[:, 2], ix[:, 1], ix[:, 0]))
+ ix_s = ix[order]; xyz_s = xyz[order]
+ diff = np.any(ix_s[1:] != ix_s[:-1], axis=1)
+ first = np.concatenate([[0], np.where(diff)[0] + 1])
+ sums = np.add.reduceat(xyz_s, first, axis=0)
+ counts = np.diff(np.append(first, len(xyz_s)))
+ centroids = sums / counts[:, None]
```

**`classify_ground` の変更:**

```diff
- key = ix * 73856093 ^ iy * 19349663
- order = np.argsort(key)
- ks = key[order]; zs = xyz[order, 2]; idxs = order
- u, first = np.unique(ks, return_index=True)
- counts = np.diff(np.append(first, len(ks)))
- keep = np.zeros(len(xyz), dtype=bool)
- for k in range(len(u)):
-     s, n = first[k], counts[k]
-     local = zs[s:s+n]
-     keep[idxs[s + int(np.argmin(local))]] = True
+ # (ix, iy, z) 辞書順ソート → 同セル先頭が min-Z 点
+ order = np.lexsort((xyz[:, 2], iy, ix))
+ ix_s = ix[order]; iy_s = iy[order]
+ diff_mask = np.concatenate(
+     [[True], (ix_s[1:] != ix_s[:-1]) | (iy_s[1:] != iy_s[:-1])]
+ )
+ keep_orig = order[diff_mask]
+ keep = np.zeros(len(xyz), dtype=bool)
+ keep[keep_orig] = True
```

---

### Bug 3 — `pipeline/aggregation.py` : グリッドスコアが `dz_p95` 基準で過大評価

| | 内容 |
|---|---|
| **ファイル** | `pipeline/aggregation.py` |
| **関数** | `aggregate_grid` |
| **症状** | 能登半島実データで score 2 が 64% 超え、目視より高いスコアが多発 |
| **原因** | `dz_p95`（\|dz\| の 95 パーセンタイル）でスコアを算出していたため、数点の外れ値でスコアが最大値まで跳ね上がっていた |

```diff
- # dz_p95 基準（外れ値に過敏）
- score = int(score_by_thresholds(np.array([dz_p95]), thresholds)[0])
+ # dz_mean 基準（run_realdata.py・建物スコアと一致）
+ score = int(score_by_thresholds(np.array([dz_mean]), thresholds)[0])
```

---

### Bug 4 — `examples/config_realdata_osm.yaml` : DSM method が `"max"` のまま

| | 内容 |
|---|---|
| **ファイル** | `examples/config_realdata_osm.yaml` |
| **症状** | main.py 経由で実行するとほぼ全セルが score 3 になる |
| **原因** | POST が地表フィルタ済みデータなのに `method: "max"` だと PRE の屋根・樹冠と POST の地面を比較してしまう |

```diff
  difference:
    method: "dsm"
    dsm:
      resolution: 0.5
-     method: "max"
+     # POST が地表フィルタ済みの場合は "min"（地面同士の比較）
+     method: "min"
```

---

### Bug 5 — `main.py` : M3C2 有意性スコアがデッドコードになっていた

| | 内容 |
|---|---|
| **ファイル** | `main.py` |
| **症状** | `use_significance: true` + M3C2 モードでも有意性が最終スコアに反映されない |
| **原因** | Step 5 で `apply_significance` により補正した `prelim_score` が、後続の集約関数（`aggregate_grid` / `aggregate_buildings`）に渡されずに捨てられていた。集約関数は独自にスコアを再計算するため `significant` マスクのみが有効 |

```diff
- if use_sig and lod95 is not None:
-     from pipeline.scoring import score_by_thresholds
-     prelim_score = score_by_thresholds(dz, thresholds)
-     prelim_score, significant = apply_significance(dz, lod95, prelim_score)
- else:
-     significant = None
+ # significant マスクのみ構築して集約関数に渡す（prelim_score は不要）
+ if use_sig and lod95 is not None:
+     _, significant = apply_significance(dz, lod95, np.zeros_like(dz, dtype=np.int8))
+ else:
+     significant = None
```

---

### ドキュメント更新

| ファイル | 変更内容 |
|---|---|
| `D:\projects\gensai\手動実行ガイド.md` | STEP 5 のデータパスを `D:\projects\` 配下に修正。「既知バグと修正履歴」セクションを追加（Bug 1〜5 の症状・原因・修正コードを記載） |

---

### 検証

修正後、以下のユニットテストをすべて通過することを確認済み（numpy のみ使用）:

| テスト | 内容 | 結果 |
|---|---|---|
| Bug1 | PRE / POST ファイルの存在確認 | ✓ PASS |
| Bug2a | XOR ハッシュ衝突の再現と lexsort による解消 | ✓ PASS |
| Bug2b | classify_ground の min-Z 抽出精度 | ✓ PASS |
| Bug3 | dz_mean / dz_p95 スコア差の確認 | ✓ PASS |
| Bug4 | config の method="min" 反映確認 | ✓ PASS |
| Bug5 | prelim_score 削除・significant-only パターン確認 | ✓ PASS |

検証スクリプト: `D:\projects\gensai\las_diff_pipeline\examples\outputs\verify_fixes.py`
（サンドボックスのネットワーク制約によりエンドツーエンド実行は手元環境で別途実施のこと）
