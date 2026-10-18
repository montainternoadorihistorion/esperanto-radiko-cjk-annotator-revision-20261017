# 汉字化世界语 → 字母转换应用

## 概述

本Streamlit应用将汉字化世界语还原为小写的世界语文本。常规版本选择只有 **新版（更新中）** 和 **旧版（固定）**。

## 功能

- **新版（更新中）**：反映评审期间已采用的修改，今后的修改继续加入此版。
- **旧版（固定）**：保留本轮汉字分配修改开始前的10,636行，不再更新其分配，例如 `las=留`、`emancip=放`。
- 可下载所选版本的完整CSV或两列CSV。两列CSV只是文件格式的区别，不是另一个转换模式。
- 通过侧栏 **高级：自定义CSV** 使用自己的对照表。
- 支持汉字、字母、上标识别符及词尾混排，结果全部输出为小写。
- 结果标示和下载文件名包含生成时的版本、修订编号及词典哈希。
- 输入、版本或词典修订发生变化后，必须重新转换才能下载结果。

中间快照保留在内部，不出现在常规版本选项中。以后也不向常规界面增加新的 `pre-*` 选项。

## 安装与运行

请连同 `data/`、`tools/` 等附属文件一起放置整个应用目录。`data/` 包含现行词典、固定旧词典、版本方针与来源JSON以及中间快照。`legacy/` 中保存的旧程序与界面的「旧版（固定）」不是同一概念。

```bash
pip install -r requirements.txt
streamlit run esperanto_converter_zh.py
```

浏览器没有自动打开时，请访问 `http://localhost:8501`。

## 使用方法

1. 在侧栏选择文本创建时使用的 **新版（更新中）** 或 **旧版（固定）**。
2. 输入汉字化世界语，点击「🔄 转换」。
3. 核对还原文本及结果标示的版本、修订编号。
4. 点击「📥 下载文本」保存；文件名也记录生成时的版本。

使用自己的CSV时，展开「高级：自定义CSV」，启用「使用自定义CSV」并上传文件。在此期间，上方常规版本选择不参与转换。

侧栏可下载所选版本的完整CSV与两列CSV。旧版两列CSV同样由固定旧词典生成。

**输入示例：**

```text
何时 西o 遇as 东on 和ᴷ 上置as 东an 衣on, 一 唯a 语o 获as 二 显ojn — 两 美ajn —, 和ᴷ 生成as 新a 解o.
```

**输出示例：**

```text
kiam okcidento renkontas orienton kaj surmetas orientan veston, unu sola lingvo akiras du aspektojn — ambaŭ belajn —, kaj naskiĝas nova kompreno.
```

## 版本选择与限制

程序不自动判断新旧版本。同一个 `放` 在固定旧版中还原为 `emancip`，在新版中还原为 `las`。中间版本或混合新旧分配的文本可能无法仅凭这两个版本准确还原。例如，`放is 精ˢo` 在固定旧版中为 `emancipis spermato`，在当前新版中为 `lasis silfo`，某个中间版本可能表示 `lasis spermato`。请核对创建时的版本记录与上下文。

转换按包含上标的最长键优先匹配，同长度时优先使用较小的 `priority`。最后将整个结果转为小写。相邻词根连写可能与另一个长键相同（例如 `酸乳`、`移植`），因此不保证任意文本都能唯一还原。详见 `置換アルゴリズム詳細.md`。

## 自定义CSV格式

```csv
esperanto,kanji,priority
bon,良,0
fic,藻ᶠᶜ,0
bangi,藻ᴮ,0
```

使用UTF-8编码。第一列为世界语词根，第二列为汉字表记，可选第三列为优先级；可以有标题行，也可以没有。标准词典中的 `source_root`、`source_line` 是同步核对用的附加列。

## 重新生成新版词典

整合修订仓库优先使用相邻目录 `kanji-esperanto-monaco/all.json`；独立放置应用时，使用内容相同的内置 `data/monaco_source_20261017.json`。生成前须与 `data/current_dictionary_source.json` 中已核对的SHA256一致。如果相邻来源存在但哈希不符，不会自动改用内置版本。

```bash
python tools/build_reverter_dictionary_from_all_json.py
python tools/build_snippet_csv_from_reverter_csv.py
python tools/check_dictionary_sync.py
python -m pytest -q -p no:cacheprovider
```

固定旧词典 `data/pejvo_piv_pre_las_20261017.csv` 和中间快照不重新生成。`monaco-commit.txt` 仅保留历史来源。整合仓库子目录中的CI配置不等同于会自动执行的顶层workflow。

## 常见问题

找不到标准词典时，请恢复应用目录及附属 `data/`。独自CSV通过高级功能上传。如果还原结果不符合原意，请核对文本创建时的版本、上标识别符以及词根连写情况。

## 许可证与联系

本应用可自由使用和修改。如有问题或建议，请联系开发者。

## 更新历史（当时的记录）

以下保留各次修改的实现与验证记录。中间版本选项、行数和旧界面说明代表当时的状态；当前操作以上述两版本说明为准。

2026-08-22的迁移将中文界面与日语版同步，替换了早期2,864条词典。当时标准词典为10,636行；该数字不代表当前持续更新的新版。

## 2026-10-17 果物・優先語根の承認更新

現行辞書（5列CSV、スニペット用2列CSV）は `ananas=菠`、`jakv=菠蜜`、`prioritat=优先`、`las=放`、`emancip=放ᴱ` です。旧果物表記 `菠萝` / `菠萝蜜` は逆変換専用の別名として同じ語根へ復元します。新しい入力候補への重複登録はしません。`pre-las-20261017` の旧辞書と歴史資料は変更していません。

辞書更新後の自己完結した再生成手順は次のとおりです。兄弟Monacoがなければ、承認済みハッシュ付きの同梱 `data/monaco_source_20261017.json` を使います。未承認ソースは書込み前に拒否します。

```bash
python tools/build_reverter_dictionary_from_all_json.py
python tools/build_snippet_csv_from_reverter_csv.py
python tools/check_dictionary_sync.py
python -m pytest -q -p no:cacheprovider
```

最長一致によって `菠蜜` / `菠萝蜜` を jakv、`菠菜` を spinac、`优先` を prioritat として復元します。`优` (avantaĝ)、`先` (aprior)、`蜜` (miel) の独立使用と、語尾・空白で区切られた連結は保持します。ただし漢字だけで `avantaĝ+aprior` を無区切りで書いた `优先` は prioritat と字面が同じです。辞書は任意の無区切り連結の作者意図を推測しません。必要なら元のラテン表記・明示的な区切りを使用してください。

## 2026-10-17 3語根の承認更新

ユーザー承認により `strut=鸵`、`sinergi=协同`、`oliv=榄` に更新しました。`oval=椭圆` / `elips=椭圆ᴱ` は据置です。日中逆変換では旧正表記 `鸵鸟` / `协同作用` / `橄榄` も同じ語根へ復元し、旧果物表記の互換も維持します。旧記事・旧CSVのbytesは変更しません。

現行CSVは更新済みMonacoソースのハッシュを固定して再生成します。旧3表記は逆変換専用aliasであり、Monacoの入力候補は新表記のみです。旧割当を選ぶ操作は従来どおり明示的な版選択です。

## 2026-10-17 复合词内部标识符同步

当前词典保留组成词根的上标，例如 `testikit=丸ᵀ炎ᵀ`、`orkidit=丸ᴼ炎ᵀ`。九个整体词根可能与既有成分组合或异拼词表记相冲突，因此按正本添加或保留整体标识符：`超ᴹ心ᴾˢa` 仍还原为 metapsika，`超ᴹ心ᴾˢᴹa` 则还原为 metapsikia。

包含旧表记 `丸炎ᵀ` / `丸炎` 的文章，请在侧栏选择“复合词标识符修正前（2026-10-17）”。该词典逐字节保存了更新前的 10,642 条记录。更早的 las=留 / emancip=放 文章仍应选择原有旧版。程序不猜测版本，也不会把有歧义的所有旧表记加入当前词典。切换词典后请重新转换。

`data/mirror-identifiers-20261017.json` 记录了正本哈希及限定更新项。当前 CSV 的生成命令不变，独立副本使用同步保存的 Monaco 数据；历史 CSV 不重新生成。`tests/test_mirror_identifiers.py` 检查全部更新键、旧词典键、原有成分分解、词尾及侧栏选择流程。既有无分隔复合词的歧义并未全部消除。

## 2026-10-17 stafilokok の承認更新

現行辞書と「スニペット」では、新表記 `葡球菌` と旧表記 `葡萄球菌` のどちらも `stafilokok` に復元します。入力候補用Monacoには新表記だけを収録し、旧表記は逆変換専用です。旧プロファイルCSVと従来の識別子・割り当ては保存しています。

現行辞書は10,645行です。`data/current_dictionary_source.json` が承認済みMonaco sourceと生成CSVのSHA256を記録します。兄弟Monacoがある場合はその検証済み `all.json`、単独配布時は同梱 `data/monaco_source_20261017.json` を使用します。旧上流pinへ自動で戻しません。

```bash
python -B tools/build_reverter_dictionary_from_all_json.py
python -B tools/build_snippet_csv_from_reverter_csv.py
python -B tools/check_dictionary_sync.py
python -B -m pytest -q -p no:cacheprovider
```

今回の更新根拠は `data/stafilokok-assignment-20261017.json`、回帰テストは `tests/test_stafilokok_assignment.py` です。旧表記が別語根と衝突する入力では生成を拒否します。

## 2026-10-17 四个词根的已批准更新与旧写法兼容

当前词典使用 `psitak=鹦ᴾˢ`、`uv=葡ᵁ`、`limon=柠`、`limonad=柠水`。
旧写法 `鹦鹉`、`葡萄`、`柠檬`、`柠檬水` 仅作为还原别名保留，仍还原为原词根。
`葡萄膜=uve` 和 `葡萄膜炎ᵀ=uveit` 保持不变；既有最长匹配规则会先识别这些完整写法。
`葡=vit`、`葡ᴬ=ampelops`、`鹦=papag` 等原有标识符与旧版词典选项也保持不变。

当前CSV共有10,649行（Monaco的10,639项加10个旧写法别名）。
`data/current_dictionary_source.json` 与 `data/four-shared-assignments-20261017.json` 固定再生成来源。
`python tools/build_reverter_dictionary_from_all_json.py` 和 `python tools/build_snippet_csv_from_reverter_csv.py` 使用同目录附带或相邻的已审核新词典重新生成。
`pre-las` / `pre-mirror` CSV及以前的manifest保持原字节。任意旧文本中的语义或词根组合歧义，不属于无条件唯一还原的保证范围。

回归检查：`python -m pytest -q -p no:cacheprovider`。当前全键、旧键的三种词尾、两版注入词典全文的前后比较记录保存在整合repo的 `_再点検_20261016/four_shared_assignments_20261017/`。

## 2026-10-17 uve / uveit 的追加批准

当前写法为 `uve=葡膜`、`uveit=葡膜炎ᵀ`。旧写法 `葡萄膜` / `葡萄膜炎ᵀ` 仅作为还原别名保留，仍还原为同一词根。
`uv=葡ᵁ`、`vit=葡`、`stafilokok=葡球菌` 和其他标识符保持不变。既有的最长匹配和内部标识符处理逻辑未修改。
当前CSV共10,651行（Monaco的10,639项与12个旧写法别名）。`data/current_dictionary_source.json` 与 `data/uve-assignments-20261017.json` 固定已审核来源。
使用 `python tools/build_reverter_dictionary_from_all_json.py` 和 `python tools/build_snippet_csv_from_reverter_csv.py` 可重新生成相同CSV。
`pre-las` / `pre-mirror` CSV和旧manifest保持原字节。上一节四词根更新时的uve保留说明属于当时范围，本节为后来批准的当前值。
回归命令：`python -m pytest -q -p no:cacheprovider`。全文及旧键兼容记录位于整合repo的 `_再点検_20261016/uve_assignments_20261017/`。

## 2026-10-17 observatori 的批准更新

当前写法为 `observatori=观台`。旧写法 `天文台` 仅作为还原别名保留，仍还原为同一词根。`majest=庄严`、`subtil=精细` 及其他分配、标识符和词根分析均保持不变。
当前CSV共10,652行（Monaco 10,639项＋13个旧写法别名）。`data/current_dictionary_source.json` 与 `data/observatori-assignment-20261017.json` 固定已审核来源。
使用 `python tools/build_reverter_dictionary_from_all_json.py` 和 `python tools/build_snippet_csv_from_reverter_csv.py` 可重新生成相同CSV。
`pre-las` / `pre-mirror` CSV与旧manifest保持原字节。回归命令：`python -m pytest -q -p no:cacheprovider`。全文及旧键兼容记录位于整合repo的 `_再点検_20261016/observatori_assignment_20261017/`。

## 2026-10-17 三个词根缩写及旧文词典

当前写法为 `risort=簧`、`anĉ=簧ᴬ`、`lantern=灯ᴸᴺ`、`lubrik=滑ᴸ`。`pland=足底` 和其他标识符保持不变。
旧写法 `弹簧` / `灯笼` / `润滑` 作为现行词典的还原别名保留。但旧的无标识符 `簧` 代表anĉ，现行代表risort。阅读旧文请明确选择 **「三个词根缩写前（簧=anĉ，2026-10-17）」**，不会自动判断或让同一个字同时映射两个词根。
这个选项完整保存修改前的10,652行CSV。可在界面下载旧词典及旧代码片段CSV：[旧完整CSV](data/pejvo_piv_pre_three_short_20261017.csv) / [旧两列CSV](data/snippet_pre_three_short_20261017.csv)。更换选项后请重新转换。
当前CSV共10,655行（Monaco10,639项＋16个旧写法别名）。`data/current_dictionary_source.json` 与 `data/three-short-assignments-20261017.json` 固定正本、来源与旧profile的SHA。
用 `python tools/build_reverter_dictionary_from_all_json.py` 和 `python tools/build_snippet_csv_from_reverter_csv.py` 可重新生成相同现行CSV。pre-las/pre-mirror和旧manifest保持原字节。
回归命令：`python -m pytest -q -p no:cacheprovider`。全文、旧键与旧词典选择记录位于整合repo `_再点検_20261016/three_short_assignments_20261017/`。



## 2026-10-17 protez / ranc の承認更新

現行辞書を `protez=假体`、`ranc=酸败` に更新しました。義肢だけでなく義歯なども含む意味範囲、および油脂の酸敗を表す字義に合わせた承認済み変更です。両語根に追加の識別子は不要です。`hangar=棚库`、`kontest=异议`、`cisticerk=囊尾虫`、`kruc=十字` は維持します。

旧 `假肢` と `哈喇` は逆変換専用の互換キーとして残し、同じ語根へ戻します。旧辞書プロファイルと変換アルゴリズムは変更していません。現行10,657行はMonaco10,639項目と旧表記18行です。生成元とSHA256は `data/current_dictionary_source.json`、今回の対象限定manifestは `data/protez-ranc-assignments-20261017.json` に記録しています。


## 2026-10-17 krep / difrakt / mortez / meger の承認更新

現行辞書を `krep=皱布`、`difrakt=绕射`、`mortez=卯`、`meger=恶女` に更新しました。絹に限定しない縮緬状の布、回り込みという回折の手掛かり、ほぞ穴を指せる単字「卯」、性格を表す「恶」と女性を表す「女」という承認理由に基づきます。4語根とも追加識別子は不要です。

旧 `皱绸`、`衍射`、`卯眼`、`悍妇` は逆変換専用の互換キーとして保持します。変換アルゴリズムと旧辞書プロファイルは変更しません。現行10,661行はMonaco10,639項目と旧表記22行です。生成元・SHA256は `data/current_dictionary_source.json`、対象限定manifestは `data/four-reviewed-assignments-20261017.json` に記録しています。


## 2026-10-17 sutur / fraj の承認更新

現行辞書を `sutur=缝ˢᴿ`、`fraj=卵ᶠ` に更新しました。傷の縫合・接合線を既存「缝」と共有し、魚やカエルなどの卵の集まりを魚に限定せず「卵」で表す承認済み変更です。`prism=棱镜` は維持します。

旧 `缝合`、`鱼卵` は逆変換専用キーとして残し、同じ語根へ戻します。`kudr=缝`、`steb=缝ˢ`、`ov=卵`、`ovol=卵ᴼᴸ`、`kojon=卵ᴷ` を含む既存対応・識別子と旧辞書プロファイルを保持します。現行10,663行はMonaco10,639項目と旧表記24行です。生成元・SHA256は `data/current_dictionary_source.json`、対象限定manifestは `data/sutur-fraj-assignments-20261017.json` に記録しています。


## 2026-10-17 nostalgi / onk / fortres の承認更新

`nostalgi=怀ᴺ`、`onk=瘤ᴼ`、`fortres=堡ᶠᴿ` を採用し、忠実な成分描画を保つため `onkogen=瘤ᴼ生ᴳ`、`onkologi=瘤ᴼ学ᴸᴳ` へ同期します。故郷等を懐かしむ意味を怀、腫瘍を瘤、要塞を堡で示す既用字共有です。`koincid=巧合` を維持し、未承認のsatir/sperm/ĉur等は変更しません。

旧 `怀旧`、`肿瘤`、`堡垒`、`肿瘤生ᴳ`、`肿瘤学ᴸᴳ` は逆変換専用キーとして保持し、現在の各語根へ戻します。旧キーの所有者移動はありません。現在の10,668行はMonaco10,639項目と旧表記29行です。`data/current_dictionary_source.json` と `data/nostalgi-onk-fortres-assignments-20261017.json` に生成元とSHAを保存し、旧プロファイルは不変です。通常の入力語根分解を新設する変更ではありません。


## 2026-10-17 satir の短縮と識別子の同期

`讽` 自体の風刺の意味を採用し、`satir=讽` とします。現行識別子の算法に従い `karikatur=讽ᴷ`、`sarkasm=讽ˢᴿ` へ同期します。spermatozo の新規割当は偽分解の再検討が必要なため保留します。`sperm=精液`、`ĉur=精液ᶜ̂`、`spermat=精ˢ` は維持し、greft/dot/konfisk/monark 系列も変更しません。

**旧文の `讽` を karikatur に戻す場合は、画面で「satir変更前（2026-10-17）」を選択してください。** 中国語画面では「satir修改前（2026-10-17）」です。この版は変更直前の全10,668行と2列CSVをそのまま保存し。版の自動推定は行いません。現行での無印 `讽` は satir です。版を切り替えた直後には前回結果を無効にし、再変換するまで結果ダウンロードを無効にします。

旧 `讽刺→satir`、`讽ˢ→sarkasm` は衝突しない逆変換専用キーとして現行にも保持します。旧 `讽→karikatur` は現行aliasに追加せず、保存済み旧版で保護します。現行はMonaco10,639項目と旧表記31行の計10,670行。`data/current_dictionary_source.json` と `data/satir-assignment-20261017.json` に出典・旧版SHA・所有移動を記録しています。


## 2026-10-18 精子と精液の区別

最新のユーザー指定に従い、植物語を含めてspermat系列の共用表記を「精子」とします。spermat=精子、spermati=精子ˢᴵ、新規spermatozo=精子ˢᶻ、鏡像3根spermatocit=精子胞ᶜᴵ、spermatofit=精子植ᶠ、spermatogenez=精子源ᴳを同期しました。固定表記の採用であり、種子植物を動物の精子と定義する変更ではありません。正本と前方アプリの注釈は元の植物語義を保持します。sperm=精液、ĉur=精液ᶜ̂、植物別義の种ˢᴿ→spermは維持します。

実算法でsilf=精ˢᴸ→精ˢとなり、旧精ˢの復元先がspermatからsilfへ移ります。**旧文で精ˢがspermatを表す場合は「精子・精液の区別変更前（2026-10-18）」を選択してください。** 中国語画面は「精子与精液区分修改前（2026-10-18）」です。変更直前の全10,670行と2列CSVを保存し、版選択で前回結果とそのダウンロードを再変換まで無効化します。自動判定はしません。

衝突しない旧精ˢᴸ→silf、精ˢᴵ→spermati、鏡像3根の旧形は現行の逆変換専用aliasとして保持します。現行はMonaco10,640項目＋旧表記36行＝10,676行です。今回manifestはdata/sperm-distinction-20261018.json。以前の保留記録や版別辞書はその時点の記録として変更していません。


## 2026-10-18 移植・妆の割当

ユーザーの採用に従い、greft=移植、dot=妆、実識別子算法に従うtualet=妆ᵀを同期しました。旧嫁接→greft、嫁妆→dotは現行辞書の逆変換専用別名として保持します。現行はMonaco10,640項目と旧表記38行の計10,678行です。注釈の接ぎ木・組織や器官の移植、持参金・天賦の語義を変更するものではありません。

**旧文の妆をtualetへ戻す場合は「移植・妆の割当変更前（2026-10-18）」を選択してください。** 中国語画面では「移植与妆分配修改前（2026-10-18）」です。変更直前の全10,676行と2列CSVを保存し、精子系列を含むその時点の割当を保ちます。版変更後は再変換するまで旧結果のダウンロードを無効にします。版の自動判定はしません。

旧文で移(translaci)＋植(plant)が連続する場合も、この旧版で復元してください。現行の最長一致では移植をgreftと読みます。既存配信コーパスで移植の連続は検出されませんでしたが、任意の連結文すべてが一意に復元できるという保証ではありません。たとえば人工的な境界試験の移植oは旧版でtranslaciplanto、現行でgreftoとなります。通常のtransplanti=越植iは不変です。以前の版別辞書はそのまま保存しています。今回manifest: data/dot-greft-20261018.json。


## 2026-10-18 通常画面を2版に統一

通常の版選択は **新版（更新中）** と **旧版（固定）** の2つです。新版は今後約1.5か月の検討期間も採用済み修正を反映し続けます。旧版は一連の漢字割当変更を始める前の `4c16c8937c601fdc149ccb8cbba1b6085cc94692` に固定し、`pre-las-20261017` の10,636行を元バイトのまま使います。旧CSV SHA256は `eed2a8bfc21a97b719e40b703ca356a6b9cd37e772811bd6d62203cfc00c4c14` です。以後、新たなpre-*を通常画面の版選択へ追加しません。

既存API ID `pejvo-piv-20260620` / `pre-las-20261017` を維持し、結果metadataに共通edition_id=current/legacyを記録します。全中間snapshotとそのAPIは内部保存します。過去のREADME節に書かれた中間版の画面選択は、その当時の仕様です。現行画面からは選択しません。2列CSVは選択版のダウンロード形式で、第三の版ではありません。カスタムCSVは独立した上級機能として残します。

結果には生成時の版・改訂番号・辞書SHAを表示し、ファイル名にも記録します。版・辞書・改訂番号・カスタムCSV内容が変わったら、再変換するまで前回の結果をダウンロードできません。表示中の過去結果を新しい版としてラベル変更しません。既存の変換結果本文や変換算法は変更しません。

2版だけで途中版や混在文を自動判定できるとは主張しません。例：`放is 精ˢo` は固定旧版で `emancipis spermato`、現行新版で `lasis silfo`、ある中間版では `lasis spermato` です。作成時の版情報と文脈の確認が必要です。中間snapshotはこうした履歴調査・復元のために保管します。


## 2026-10-18 固定旧版的还原补充

仅为旧版逆转换补充固定旧版正向转换产生的三种写法：`丸ᵀ炎ᵀ→testikit`、`丸ᴼ炎ᵀ→orkidit`、`兰炎ᵀ→orkidit`。旧分配、识别符和10,636行固定CSV不变，已有的 `丸炎ᵀ` / `丸炎` 仍按原样还原。新版、中间快照和自定义CSV不会自动应用这些补充。

原有完整CSV和两列CSV仍保持原样，不包含补充。旧版另提供含还原补充的三列CSV，作为自定义CSV载入后，其对应关系与应用旧版相同；这不是第三个版本。结果版本信息和文件名记录补充修订编号及SHA，重新转换前不会给以前的结果改贴新标签。依据与范围见 `data/legacy_inverse_aliases.json`。


## 2026-10-18 新版的 orkidit 还原补充

仅新增完整键 `兰炎ᵀ→orkidit`，还原新版正向转换中无词尾、形容词及动词等形式。汉字分配、识别符、分解、正本CSV及旧版三条补充均不变。只在选择新版主词典时应用，中间快照、两列片段API和自定义CSV不自动追加。已有 `丸ᴼ炎ᵀ` 以及 `兰` / `炎` 的独立还原保持不变。

原有完整CSV与两列CSV字节不变，不含补充；另提供含还原补充的三列CSV，可作为自定义CSV再现相同结果。这不是第三个版本。结果标示及文件名包含补充修订编号和SHA，重新转换前不为旧结果改贴新标签。

`data/current_inverse_aliases.json` 固定经审核的新版CSV哈希及词典修订编号。今后更新新版词典后，必须重新审核所有既有键、词根边界和归属冲突，才能更新固定值。不一致时明确报错要求重新审核，不自动推进固定值。原有正本生成器不变，补充保存在独立文件中。

## 2026-10-18 补充对应唯一的缺失逆转换键

根据全量审核，新版新增7条、旧版新增15条还原补充。上文的“1条”“3条”是之前阶段的记录，目前总数为新版8条、旧版18条。补充包括 `盐ᴬ→at`、`盐ᴵ→it`、`炎ᵀ→it` 等，均已在实际正向输出中核对对应关系及改善效果。

汉字分配、识别符、正本CSV、词根分解及既有键的归属不变，全文最长匹配算法也不变。完整正本CSV与两列CSV仍不含补充，另提供与应用所选版本相同的含补充CSV。修订编号为 `current-unique-inverse-20261018-v2` / `legacy-unique-inverse-20261018-v2`。同一写法对应多个原文的歧义不在本次修改范围内。

## 2026-10-18 复合写法缺失键与识别符边界

根据用户批准的范围，新版新增1条、固定旧版新增140条还原补充，包括新版 `远复ᴷ→telekopi`，旧版 `蜗牛→limak`、`醋盐ᴬ→acetat`、`微切ᵀᴼ→mikrotom` 等实际正向转换产生的写法。保留此前的所有补充，目前总数为新版9条、旧版158条。批准的新增集合固定在 `tests/fixtures/compound_inverse_additions_20261018.json`。

汉字分配、识别符、正本CSV、正向词根分解和既有键的对应关系不变。用户允许 `adiaŭi／revidi→再见i` 等共用写法的歧义，本次不通过上下文猜测原文。`中肠ᴱ→mezenter` 不在新增集合中。

逆转换不再在上标识别符中间匹配较短的键。例如 `远复ᴷˢ` 不会截取 `远复ᴷ`，而按既有的 `远＋复ᴷˢ` 还原为 `telekompleks`。识别符包括组合帽号、短音符，未知识别符连续串保留，不从中间重新匹配。完整键之间仍使用原来的最长匹配及优先级。边界规则也适用于中间快照和自定义CSV，但这些词典不会自动获得新增补充键。

补充修订编号为 `current-compound-inverse-20261018-v3` / `legacy-compound-inverse-20261018-v3`。原有完整CSV、两列CSV字节不变，只有含还原补充的CSV增加这些对应。界面、结果版本信息和下载文件名继续与所选版本及补充修订编号对应。
