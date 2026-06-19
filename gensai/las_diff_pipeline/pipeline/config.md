# `config.py` コード解説

このファイルは、YAML形式の設定ファイルを読み込み、Pythonの中で扱いやすい `Config` オブジェクトとして管理するためのコードです。

主な役割は次の3つです。

1. YAMLファイルを読み込む
2. 設定項目を `config.io` や `config.scoring` のように取り出せるようにする
3. 設定ファイルから見た相対パスを、絶対パスに変換する

---

## 全体像

```python
"""YAML config loader."""
```

このファイルの説明文です。

意味は「YAML設定ファイルを読み込むためのコード」です。

発表では、次のように説明できます。

> このファイルは、解析処理に使う設定ファイルを読み込み、プログラム内で扱いやすい形に変換する役割を持っています。

---

## 1. 将来のPython記法に対応するための記述

```python
from __future__ import annotations
```

これは、型ヒントの扱いを新しいPythonの仕様に近づけるための記述です。

このコードでは、後の部分に次のような型ヒントが出てきます。

```python
def resolve_path(self, p: str | Path) -> Path:
```

`str | Path` は、「文字列またはPath型」という意味です。

`from __future__ import annotations` を書くことで、型ヒントをより柔軟に扱えるようになります。

発表では、細かい内部仕様まで説明する必要はありません。

> ここでは、型ヒントを新しい書き方で使えるようにするための準備をしています。

と説明すれば十分です。

---

## 2. dataclass と field の読み込み

```python
from dataclasses import dataclass, field
```

`dataclass` は、データをまとめるクラスを簡単に作るための機能です。

このコードでは、後で出てくる `Config` クラスに使われています。

通常のクラスでは、初期化処理を自分で書く必要があります。

例えば、普通に書くと次のようになります。

```python
class Config:
    def __init__(self, raw, config_path):
        self.raw = raw
        self.config_path = config_path
```

しかし、`dataclass` を使うと、次のように短く書けます。

```python
@dataclass
class Config:
    raw: dict
    config_path: Path
```

これだけで、`raw` と `config_path` を受け取る初期化処理が自動で作られます。

一方、`field` は `dataclass` の初期値などを細かく設定するときに使います。

ただし、この `config.py` では `field` は読み込まれていますが、実際には使われていません。

発表では、次のように説明できます。

> `dataclass` は設定情報をまとめるクラスを簡潔に書くための機能です。`field` も dataclass 用の機能ですが、このファイル内では使われていません。

---

## 3. Path の読み込み

```python
from pathlib import Path
```

`Path` は、ファイルやフォルダのパスを扱いやすくするための機能です。

例えば、次のような文字列のパスを、

```python
"config/settings.yaml"
```

`Path` を使うと、ファイルパスとして扱いやすいオブジェクトにできます。

```python
Path("config/settings.yaml")
```

このコードでは、設定ファイルの場所を扱ったり、相対パスを絶対パスに変換したりするために使われています。

発表では、次のように説明できます。

> `Path` は、設定ファイルの場所や出力先のパスを安全に扱うために使っています。

---

## 4. Any の読み込み

```python
from typing import Any
```

`Any` は、「どんな型でもよい」という意味の型ヒントです。

例えば、文字列でも数値でもリストでも辞書でもよい場合に使います。

ただし、この `config.py` では `Any` は読み込まれていますが、実際には使われていません。

発表では、次のように説明できます。

> `Any` は任意の型を表す型ヒントですが、このファイルでは未使用です。

---

## 5. yaml の読み込み

```python
import yaml
```

`yaml` は、YAML形式のファイルを読み込むためのライブラリです。

YAMLは、設定ファイルでよく使われる形式です。

例えば、次のような形です。

```yaml
io:
  output_dir: outputs
scoring:
  thresholds: [0.3, 1.0, 3.0]
```

このコードでは、後で出てくる `load_config` 関数の中で、

```python
yaml.safe_load(f)
```

としてYAMLファイルを読み込んでいます。

発表では、次のように説明できます。

> `yaml` は、外部の設定ファイルをPythonの辞書として読み込むために使っています。

---

# Config クラス

```python
@dataclass
class Config:
```

ここから `Config` クラスを定義しています。

`@dataclass` が付いているため、このクラスは設定データをまとめるためのクラスとして簡潔に書かれています。

発表では、次のように説明できます。

> `Config` クラスは、読み込んだYAML設定をまとめて保持し、各項目にアクセスしやすくするためのクラスです。

---

## 6. raw

```python
    raw: dict
```

`raw` は、YAMLファイルを読み込んだ結果をそのまま保存する辞書です。

例えばYAMLに次のように書かれていた場合、

```yaml
io:
  output_dir: outputs
```

Pythonでは、おおよそ次のような辞書になります。

```python
{
    "io": {
        "output_dir": "outputs"
    }
}
```

この辞書全体を `raw` に保存します。

発表では、次のように説明できます。

> `raw` には、YAMLファイルの内容がPythonの辞書としてそのまま入ります。

---

## 7. config_path

```python
    config_path: Path
```

`config_path` は、読み込んだ設定ファイル自体のパスです。

なぜ設定ファイルの場所を保存するかというと、設定ファイルの中に相対パスが書かれていた場合に、その相対パスを正しく解決するためです。

例えば、設定ファイルが次の場所にあるとします。

```text
project/config/settings.yaml
```

その中に、次のように書かれていた場合、

```yaml
input: data/sample.las
```

これは設定ファイルから見た相対パスとして解釈する必要があります。

そのため、`config_path` を持っておくことで、後で正しい絶対パスに変換できます。

発表では、次のように説明できます。

> `config_path` は、設定ファイルの場所を記録しておき、相対パスを正しく扱うために使います。

---

# property による設定項目の取り出し

このクラスでは、`@property` が何度も出てきます。

`@property` を使うと、メソッドを変数のように呼び出せます。

例えば、次のようなメソッドは、

```python
@property
def io(self) -> dict:
    return self.raw.get("io", {})
```

呼び出すときに、

```python
config.io()
```

ではなく、

```python
config.io
```

のように書けます。

発表では、次のように説明できます。

> `@property` を使うことで、設定項目を関数のように呼び出すのではなく、属性のように自然に取り出せるようにしています。

---

## 8. io プロパティ

```python
    @property
    def io(self) -> dict:
        return self.raw.get("io", {})
```

`io` という設定項目を取り出すためのプロパティです。

`self.raw.get("io", {})` は、`raw` の中から `"io"` というキーを探しています。

もし `"io"` があれば、その値を返します。

もし `"io"` がなければ、空の辞書 `{}` を返します。

つまり、YAMLに `io` の設定が書かれていなくてもエラーにならないようにしています。

発表では、次のように説明できます。

> `io` プロパティは、入出力に関する設定を取り出します。設定が存在しない場合は空の辞書を返します。

---

## 9. output_dir プロパティ

```python
    @property
    def output_dir(self) -> str:
        return self.io.get("output_dir", "outputs")
```

`output_dir` は、出力先フォルダを取り出すためのプロパティです。

ここでは、まず `self.io` にアクセスしています。

`self.io` は、先ほどの `io` プロパティです。

つまり、YAMLの `io` セクションの中から、`output_dir` を探しています。

```python
self.io.get("output_dir", "outputs")
```

これは、`output_dir` が設定されていればその値を返し、設定されていなければ `"outputs"` を返すという意味です。

例えば、YAMLに次のように書かれていれば、

```yaml
io:
  output_dir: results
```

`config.output_dir` は `"results"` になります。

一方、`output_dir` が書かれていなければ、デフォルトで `"outputs"` になります。

発表では、次のように説明できます。

> `output_dir` は出力先フォルダを取得します。設定がない場合は、デフォルトで `outputs` を使います。

---

## 10. crs プロパティ

```python
    @property
    def crs(self) -> dict:
        return self.raw.get("crs", {})
```

`crs` 設定を取り出します。

`crs` は座標参照系、つまり地理データの座標系に関する設定だと考えられます。

点群や建物ポリゴンなど、地理空間データを扱う場合、座標系を正しく指定する必要があります。

設定がない場合は空の辞書 `{}` を返します。

発表では、次のように説明できます。

> `crs` は、座標系に関する設定を取り出すプロパティです。

---

## 11. preprocess プロパティ

```python
    @property
    def preprocess(self) -> dict:
        return self.raw.get("preprocess", {})
```

`preprocess` 設定を取り出します。

`preprocess` は前処理という意味です。

点群解析では、ノイズ除去、フィルタリング、範囲指定などの処理が前処理に含まれることがあります。

設定がない場合は空の辞書を返します。

発表では、次のように説明できます。

> `preprocess` は、解析前の前処理に関する設定を取り出します。

---

## 12. registration プロパティ

```python
    @property
    def registration(self) -> dict:
        return self.raw.get("registration", {})
```

`registration` 設定を取り出します。

`registration` は、点群同士の位置合わせを意味することが多いです。

例えば、災害前と災害後の点群を比較する場合、両者の座標位置を合わせる必要があります。

この位置合わせに関する設定を取り出すためのプロパティです。

発表では、次のように説明できます。

> `registration` は、複数の点群を重ね合わせるための位置合わせ設定を取り出します。

---

## 13. difference プロパティ

```python
    @property
    def difference(self) -> dict:
        return self.raw.get("difference", {})
```

`difference` 設定を取り出します。

`difference` は差分という意味です。

このプロジェクトでは、変化前後の点群を比較して、`dz` のような変化量を計算していると考えられます。

その差分計算に関する設定を取得するプロパティです。

発表では、次のように説明できます。

> `difference` は、変化前後の点群の差分計算に関する設定を取り出します。

---

## 14. scoring プロパティ

```python
    @property
    def scoring(self) -> dict:
        return self.raw.get("scoring", {})
```

`scoring` 設定を取り出します。

`scoring` は、被害度などのスコアを計算するための設定です。

例えば、どの程度の変化量をどのスコアに対応させるか、といったしきい値が含まれる可能性があります。

発表では、次のように説明できます。

> `scoring` は、変化量から被害スコアを決めるための設定を取り出します。

---

## 15. aggregation プロパティ

```python
    @property
    def aggregation(self) -> dict:
        return self.raw.get("aggregation", {})
```

`aggregation` 設定を取り出します。

`aggregation` は集計という意味です。

前に見た `aggregation.py` では、グリッド単位や建物単位で点群の変化量を集計していました。

そのため、ここで取り出す `aggregation` 設定には、グリッドサイズ、建物ポリゴンの取得方法、最小点数などの設定が含まれると考えられます。

発表では、次のように説明できます。

> `aggregation` は、グリッド集計や建物単位集計に関する設定を取り出します。

---

# resolve_path メソッド

```python
    def resolve_path(self, p: str | Path) -> Path:
```

ここでは、`resolve_path` というメソッドを定義しています。

このメソッドは、受け取ったパスを絶対パスに変換するためのものです。

引数 `p` は、文字列または `Path` 型を受け取ります。

戻り値は `Path` 型です。

発表では、次のように説明できます。

> `resolve_path` は、設定ファイル内に書かれたパスを、実際に使える絶対パスに直すためのメソッドです。

---

## 16. resolve_path の説明文

```python
        """config file からの相対パスを絶対パスに解決."""
```

このメソッドの説明文です。

意味は、「設定ファイルから見た相対パスを絶対パスに変換する」ということです。

---

## 17. Path オブジェクトへの変換

```python
        p = Path(p)
```

受け取った `p` を `Path` オブジェクトに変換しています。

`p` が文字列で渡されても、ここで `Path` に変換することで、後の処理を統一できます。

例えば、

```python
p = "data/input.las"
```

のような文字列でも、

```python
Path("data/input.las")
```

として扱えるようになります。

発表では、次のように説明できます。

> まず、文字列で渡されたパスも扱いやすいように `Path` 型へ変換しています。

---

## 18. 絶対パスかどうかの判定

```python
        if p.is_absolute():
            return p
```

`p.is_absolute()` は、そのパスがすでに絶対パスかどうかを調べます。

絶対パスとは、ファイルの場所を最初から完全に示しているパスです。

例えばWindowsなら、

```text
C:\Users\user\project\data\input.las
```

のようなパスです。

すでに絶対パスであれば、変換する必要がないので、そのまま返します。

発表では、次のように説明できます。

> もし渡されたパスがすでに絶対パスなら、そのまま返します。

---

## 19. 相対パスを絶対パスに変換

```python
        return (self.config_path.parent / p).resolve()
```

ここが `resolve_path` の中心です。

渡された `p` が相対パスだった場合、設定ファイルが置かれているフォルダを基準にして、絶対パスへ変換します。

`self.config_path.parent` は、設定ファイルが入っているフォルダを表します。

例えば設定ファイルが、

```text
project/config/settings.yaml
```

にある場合、`self.config_path.parent` は、

```text
project/config
```

になります。

そこに `p` をつなげます。

```python
self.config_path.parent / p
```

最後の `.resolve()` によって、実際の絶対パスに変換します。

発表では、次のように説明できます。

> 相対パスの場合は、設定ファイルがあるフォルダを基準にして絶対パスへ変換しています。これにより、どこからプログラムを実行しても、設定ファイル内のパスを正しく参照できます。

---

# load_config 関数

```python
def load_config(path: str | Path) -> Config:
```

ここから `load_config` 関数を定義しています。

この関数は、YAML設定ファイルを読み込み、`Config` オブジェクトとして返すための関数です。

引数 `path` は、文字列または `Path` 型で受け取ります。

戻り値は `Config` 型です。

発表では、次のように説明できます。

> `load_config` は、指定されたYAMLファイルを読み込み、設定を扱いやすい `Config` オブジェクトに変換する関数です。

---

## 20. パスを絶対パスに変換

```python
    p = Path(path).resolve()
```

受け取った設定ファイルのパスを `Path` に変換し、さらに絶対パスにしています。

これにより、後の処理で設定ファイルの場所を正確に扱えます。

発表では、次のように説明できます。

> 最初に、指定された設定ファイルのパスを絶対パスに変換しています。

---

## 21. YAMLファイルを開く

```python
    with open(p, "r", encoding="utf-8") as f:
```

指定された設定ファイルを読み込みモードで開いています。

`"r"` は読み込みモードです。

`encoding="utf-8"` は、文字コードをUTF-8として読み込むという意味です。

`with open(...) as f:` と書くことで、ファイルを使い終わった後に自動で閉じてくれます。

発表では、次のように説明できます。

> 設定ファイルをUTF-8の読み込みモードで開いています。`with` を使うことで、読み込み後に自動でファイルが閉じられます。

---

## 22. YAMLをPythonのデータに変換

```python
        raw = yaml.safe_load(f)
```

ここで、YAMLファイルの内容をPythonのデータに変換しています。

通常、YAMLの設定はPythonでは辞書として読み込まれます。

例えば、

```yaml
io:
  output_dir: outputs
```

は、次のような辞書になります。

```python
{
    "io": {
        "output_dir": "outputs"
    }
}
```

`safe_load` は、安全にYAMLを読み込むための関数です。

発表では、次のように説明できます。

> `yaml.safe_load` によって、YAML形式の設定ファイルをPythonの辞書に変換しています。

---

## 23. 読み込んだ内容が辞書か確認

```python
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid YAML at {p}")
```

YAMLを読み込んだ結果が辞書かどうかを確認しています。

この設定ファイルでは、トップレベルが辞書形式であることを想定しています。

例えば、正しい形式は次のようなものです。

```yaml
io:
  output_dir: outputs
crs:
  epsg: 6677
```

一方、次のようにリストだけが書かれている場合は、このコードでは不正と判断されます。

```yaml
- item1
- item2
```

辞書でなければ、`ValueError` を出して処理を止めます。

発表では、次のように説明できます。

> 読み込んだYAMLが想定通り辞書形式になっているか確認し、違う形式ならエラーにしています。

---

## 24. Config オブジェクトを返す

```python
    return Config(raw=raw, config_path=p)
```

最後に、読み込んだ設定内容 `raw` と、設定ファイルのパス `p` を使って、`Config` オブジェクトを作成して返します。

これにより、他のプログラムでは、

```python
config = load_config("settings.yaml")
```

のように設定を読み込み、

```python
config.output_dir
config.scoring
config.aggregation
```

のように設定項目へアクセスできるようになります。

発表では、次のように説明できます。

> 最後に、YAMLの中身と設定ファイルの場所を `Config` クラスにまとめて返しています。

---

# このファイル全体のまとめ

この `config.py` は、YAML形式の設定ファイルを読み込んで、プログラム内で扱いやすくするためのコードです。

流れとしては、まず `load_config` 関数でYAMLファイルを読み込みます。読み込んだ内容が辞書形式であることを確認したうえで、`Config` クラスのオブジェクトとして返します。`Config` クラスでは、`io`、`crs`、`preprocess`、`registration`、`difference`、`scoring`、`aggregation` などの設定項目をプロパティとして取り出せるようにしています。また、`resolve_path` メソッドによって、設定ファイル内に書かれた相対パスを、設定ファイルの場所を基準にした絶対パスへ変換できます。

---

# 発表用の短い説明例

このファイルは、解析処理に必要な設定をYAMLファイルから読み込むためのコードです。`load_config` 関数で指定されたYAMLファイルを開き、`yaml.safe_load` によってPythonの辞書として読み込みます。その内容を `Config` クラスに渡すことで、`config.io` や `config.scoring`、`config.aggregation` のように、各設定項目へ簡単にアクセスできるようになります。また、`resolve_path` メソッドでは、設定ファイルから見た相対パスを絶対パスへ変換しており、プログラムをどの場所から実行してもファイルを正しく参照できるようにしています。

---

# 特に説明すべきポイント

## 1. YAMLを読み込むためのファイルである

このコードの中心は、`load_config` 関数です。

YAMLファイルを読み込み、Pythonの辞書に変換しています。

## 2. Config クラスで設定を扱いやすくしている

YAMLの中身をそのまま辞書として扱うのではなく、`Config` クラスにまとめることで、設定項目へアクセスしやすくしています。

## 3. @property によって自然に設定を取り出せる

`config.io`、`config.output_dir`、`config.scoring` のように、関数呼び出しではなく属性のように設定を取り出せます。

## 4. 設定がない場合もエラーになりにくい

多くのプロパティで、

```python
self.raw.get("キー", {})
```

という書き方をしています。

これにより、設定項目が存在しない場合でも空の辞書を返し、すぐにエラーにならないようにしています。

## 5. 相対パスを正しく扱える

`resolve_path` によって、設定ファイルに書かれた相対パスを、設定ファイルの場所を基準にして絶対パスに直しています。

これは、実行場所が変わってもファイル参照が壊れにくくなる重要な処理です。

---

# 1文でまとめるなら

`config.py` は、YAML設定ファイルを読み込み、各設定項目へのアクセスとパス解決を行いやすくするための設定管理用コードです。
