# export.py — GeoJSONへの書き出し

解析結果のGeoDataFrame（ポリゴンや点のベクターデータ）をGeoJSON形式に変換して保存するモジュールです。座標系の自動変換を行い、WebマップやGISソフトで直接開ける形式に仕上げる。

---

## `export_geojson(gdf, path, target_epsg=4326)`

### 引数

| 引数 | 型 | デフォルト | 内容 |
|---|---|---|---|
| `gdf` | `GeoDataFrame` | — | 書き出すベクターデータ |
| `path` | `str / Path` | — | 出力先ファイルパス（例：`./output/damage.geojson`） |
| `target_epsg` | `int` | `4326` | 出力座標系のEPSGコード。通常はWGS84（4326）のまま使用 |

### 戻り値

なし。ファイルへの書き出しのみ行う。

---

## 処理の流れ

```
入力 GeoDataFrame
      │
      ├─ CRSが未設定？
      │     → WARNING ログを出力してそのまま書き出す
      │
      ├─ CRSが target_epsg と異なる？
      │     → INFO ログ（フィーチャ数・変換前後のEPSG）を出力
      │     → gdf.to_crs() で再投影
      │     → 再投影後のデータを書き出す
      │
      └─ CRSが target_epsg と一致？
            → そのまま書き出す
                  │
                  ↓
            GeoJSON ファイル
```

---

## ログ出力

処理の各ステップで以下のログが記録されます。

| レベル | タイミング | 内容 |
|---|---|---|
| `WARNING` | CRSが未設定のとき | 再投影できない旨を通知 |
| `INFO` | 再投影を実行するとき | フィーチャ数・変換前後のEPSGコードを記録 |
| `INFO` | 書き出し完了時 | 出力パスとフィーチャ数を記録 |

ログ出力例：
```
WARNING  GeoDataFrame has no CRS; cannot reproject
INFO     Reprojecting 142 features: EPSG:6668 -> EPSG:4326
INFO     Wrote GeoJSON: ./output/damage.geojson (N=142)
```

---

## 出力ファイルについて

- フォーマット：**GeoJSON**（RFC 7946準拠）
- 座標系：デフォルトは **EPSG:4326（WGS84 / 緯度経度）**
- 出力先ディレクトリが存在しない場合は**自動作成**されます。

出力されたGeoJSONは以下のツールで直接開ける。

| ツール | 用途 |
|---|---|
| QGIS / ArcGIS | デスクトップGISでの可視化・編集 |
| Leaflet / Mapbox | WebマップへのオーバーレイGISデータとして利用 |
| geojson.io | ブラウザ上でのクイック確認 |

---

## 使用例

```python
from export import export_geojson

# 解析済みのGeoDataFrameをWGS84で書き出す
export_geojson(damage_gdf, "./output/damage.geojson")

# 座標系を明示的に指定する場合（例：日本測地系2011）
export_geojson(damage_gdf, "./output/damage_jgd.geojson", target_epsg=6668)
```

---

## 依存ライブラリ

| ライブラリ | 用途 | 必須 / オプション |
|---|---|---|
| `geopandas` | ベクターデータ操作・GeoJSON出力 | 必須 |
| `pyproj` | CRS変換（`to_crs()`の内部で使用） | 推奨 |
