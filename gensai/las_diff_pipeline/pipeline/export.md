# export.py — GeoJSONへの書き出し

解析結果のGeoDataFrame（ポリゴンや点のベクターデータ）をGeoJSON形式に変換して保存するモジュールです。WebマップやGISソフトで直接開ける形式に仕上げます。

---

## `export_geojson(gdf, path, target_epsg=4326)`

### 引数

| 引数 | 型 | 内容 |
|---|---|---|
| `gdf` | `GeoDataFrame` | 書き出すベクターデータ |
| `path` | `str / Path` | 出力先ファイルパス |
| `target_epsg` | `int` | 出力座標系（デフォルト：4326 / WGS84） |

---

## 処理の流れ

```
CRSが未設定？
  → 警告ログを出してそのまま書き出す

CRSが target_epsg と異なる？
  → 自動で再投影してから書き出す

CRSが一致している？
  → そのまま書き出す
```

---

## 注意点

- 出力先ディレクトリが存在しない場合は自動作成されます。
- 出力されたGeoJSONはLeaflet・MapboxなどのWebGISライブラリやデスクトップのQGISで直接開けます。

---

## 依存ライブラリ

| ライブラリ | 用途 | 必須 / オプション |
|---|---|---|
| `geopandas` | ベクターデータ操作・GeoJSON出力 | 必須 |
| `pyproj` | CRS変換 | 推奨 |
