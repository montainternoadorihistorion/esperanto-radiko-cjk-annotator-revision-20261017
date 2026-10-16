# エスペラント注釈ルビ・漢字化アプリ 改訂版

日中韓3言語の Streamlit アプリです。エスペラント文を語根分解し、注釈ルビ・漢字ルビ・漢字化の純粋置換で表示します。2026年10月の修正を反映し、Streamlit Community Cloud で動作確認した公開リポジトリです。

## 公開アプリ

- [日本語版](https://esperanto-cjk-revision-ja-20261017.streamlit.app/)
- [中国語版](https://esperanto-cjk-revision-zh-20261017.streamlit.app/)
- [韓国語版](https://esperanto-cjk-revision-ko-20261017.streamlit.app/)

2026年10月17日（日本時間）、実際の Cloud アプリを Chrome で操作し、3言語×3モード、手動補正・データダウンロードの計6ページ、メインページへの復帰後の再変換を確認しました。実行環境は Python **3.12.15** / Streamlit **1.50.0** / pandas **2.3.3**、確認対象のソースは `b4f7cee` です。

中国語 `akuzativ/o` と韓国語 `um` の語義プレビュー、3言語のCSVダウンロードとリポジトリ内データのバイト一致、日本語版でダウンロードした注釈HTMLの本文・ルビも確認しています。[Cloud確認結果](tests/cloud_smoke.json)、[CSV照合結果](tests/cloud_download_verification.json)、[変換結果HTMLの照合結果](tests/cloud_result_download_verification.json)を収録しています。確認範囲は下記の回帰入力と記載した操作経路で、全文コーパスの精度検証や長文・同時アクセスの負荷試験は含みません。

## Streamlit Community Cloud への配備

[Streamlit Community Cloud](https://share.streamlit.io/) にログインし、「Create app」から次の設定で配備します。

| 設定 | 値 |
|---|---|
| Repository | `montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017` |
| Branch | `main` |
| Main file path（日本語版） | `Esperanto-Kanji-Ruby-JA/main.py` |
| Advanced settings → Python version | `3.12` |

中国語版は `Esperanto-Kanji-Ruby-ZH/main.py`、韓国語版は `Esperanto-Kanji-Ruby-KO/main.py` を入口として、それぞれ別のアプリを配備できます。

3言語のフォルダーは同じリポジトリに置いたまま使用してください。中国語版・韓国語版の純粋置換では、日本語版フォルダー内の共通JSONを読み込みます。

依存関係は、各言語版とリポジトリ直下の `requirements.txt` に記載しています。検証時の Streamlit 1.50.0 / pandas 2.3.3 を固定しています。Cloud 共通のテーマ設定は、直下の `.streamlit/config.toml` です。

アプリ下部の「旧公開版」リンクは以前の公開先です。今回の改訂版は上記「公開アプリ」のリンクから利用できます。

配置の詳細は [Streamlit公式のファイル構成](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization) と [配備手順](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) を参照してください。

## 操作と確認例

1. メインページで注釈ルビ・漢字ルビ・純粋置換のいずれかを選びます。
2. エスペラント文を入力して変換します。自作JSONや手動補正JSONの読み込みも利用できます。
3. 結果はプレビュー、編集、ダウンロードできます。語根分解の手動補正とデータのダウンロードはサイドバーから開きます。

今回の修正を確認する入力例：

```text
@semajn@tagoj & %amiko% ŝakisto semajntagoj
```

「漢字化・純粋置換」の期待結果：

```text
周日oj & amiko 棋家o 周日oj
```

- `@...@` は囲んだ部分への局所的な変換を指定し、対応する目印は変換後に消えます。語の途中の `@semajn@tagoj` にも対応します。
- `%...%` は囲んだ部分を変換せずに残します。`%` の保護が優先するため、`%@amiko@%` は `@amiko@` として残ります。
- 空の `@@`、対応相手のない `@`、改行をまたぐ囲みは局所変換の指定として扱いません。
- 文脈のない `semajn` は `sem/a/j/n`（種に関する形容詞の複数対格）にもなり得るため、一律には週の語根へ置き換えません。週を明示する場合は `@semajn@` を使えます。`semajntagoj` 等の確認済みの語では、週の語根を保護しています。

## 今回含まれる修正

- `@...@` の検出・除去、語中の指定、長い指定、HTML記号を含む入力の処理。
- 隣接する同一語で、語境界付きの置換規則が抜けるケース。
- 確認済みの `semajn` / `ŝakist` 語族の限定的な置換データ修正。
- 中国語注釈CSVの `akuzativ` と韓国語注釈CSVの `um` の明確な誤り。
- 最新データのダウンロード先を、この改訂版の `main` に変更。
- Cloud での再実行・ページ移動時にも入口を正しく解決できるよう、作業ディレクトリを変更せず、各ファイルを基準とした絶対パスでデータを読み込むよう修正。

漢字の割り当て変更は含みません。`las`、`ananas`、`prioritat` などの検討は別途継続します。

## ローカルでの実行・検証

Python 3.12 でリポジトリ直下から実行します。

```shell
python -m pip install -r requirements.txt
python -m streamlit run Esperanto-Kanji-Ruby-JA/main.py
```

回帰確認：

```shell
python -m unittest discover -s tests -p "test_*.py"
python tests/app_ui_smoke.py
```

`tests/app_ui_smoke.py` は画面コードをローカルの Streamlit AppTest で動かし、3言語×3モード、補助6ページ、同じセッションでメインページへ戻った後の再変換と作業ディレクトリの保持を確認します。[実行結果](tests/app_ui_smoke.json)を収録しています。この AppTest と、上記の実ブラウザによる Cloud 確認は別々に実施しています。

## 収録範囲と由来

このリポジトリには、アプリの実行コード、配備済み置換JSON、対応CSV、設定、参考説明書、検証コードを収録しています。全文コーパス、個人の日記・読書資料、旧Git履歴、研究用の再生成パイプラインは含みません。それらを含む全プロジェクトの保存先は別の非公開統合リポジトリです。

旧説明書は各言語フォルダー内に参考資料として残しています。現行画面と異なる説明があるため、現在の操作・配備方法はこの README を参照してください。大JSONの全面再生成は、全資料を備えた統合プロジェクト側で実施します。

基礎となった公開アプリ：

- [Takatakatake/esperanto-radiko-cjk-annotator](https://github.com/Takatakatake/esperanto-radiko-cjk-annotator)
- [montainternoadorihistorion/esperanto-radiko-cjk-annotator](https://github.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator)（上記の fork）

元プロジェクトに記載されたデータ源は、PEJVO/PIV統合の学習者版マスター辞書、2890 Gravaj Esperantaj Vortoj、エスペラント語根→漢字割り当てマスター、および京大エス研のエスペラントHTML文書群です。元ソースに独立した LICENSE ファイルがないため、この改訂版で新たなライセンス条件は設定していません。
