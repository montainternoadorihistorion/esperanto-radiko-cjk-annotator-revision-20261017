# 汉字化世界语转换 - 使用示例

> 2026-08-22 更新：全部示例已按现行分配方案（PEJVO/PIV 2026-06-20，与 kanji-esperanto-monaco 的 all.json 同步）重写，
> 并已通过本应用逐句验证（输入→输出完全一致）。主要变化：bon=良（好 现分配给 amator）、plad=皿、hom=人（无标记）、
> manĝ=食、nun=现、spic=香、kaj=和ᴷ、konsent=赞ᴷ、akord=和ᴬ、dum=期ᴰᴹ、divers=杂、efektiv=实ᴱ、lok=处（无标记）、viand=肉（无标记）。

## 转换示例

### 示例1：基本转换

**输入（汉字化世界语）：**
```
我 听is, ke kumino 很 良e 适as 为 la 羊物a 皿o.
```

**输出（字母世界语）：**
```
mi aŭdis, ke kumino tre bone taŭgas por la ŝafaĵa plado.
```

**中文翻译：**
"我听说，孜然非常适合羊肉料理。"

---

### 示例2：完整句子

**输入（汉字化世界语）：**
```
我 听is, ke 期ᴰᴹ 反更 比 周o 和ᴷ 从 二 杂aj 人oj 内 反同aj 处oj, ke kumino 很 良e 适as 为 la 羊物a 皿o "jingisukan".
我 实ᴱe 试is kuminon 共 jingisukan, 和ᴷ 我 全e 赞ᴷas: kumino 真e 良e 和ᴬas kun la 羊物a 皿o.
从 现, 何时 我 食os jingisukan, 我 决is 全时 香i la 肉on 以 kumino.
```

**输出（字母世界语）：**
```
mi aŭdis, ke dum malpli ol semajno kaj de du diversaj homoj en malsamaj lokoj, ke kumino tre bone taŭgas por la ŝafaĵa plado "jingisukan".
mi efektive provis kuminon kun jingisukan, kaj mi ĉie konsentas: kumino vere bone akordas kun la ŝafaĵa plado.
de nun, kiam mi manĝos jingisukan, mi decidis ĉiam spici la viandon per kumino.
```

**中文翻译：**
"我听说，在不到一周的时间里，从两个不同地方的不同人那里听说，孜然非常适合羊肉料理'成吉思汗烤肉'。
我实际上尝试了孜然和成吉思汗烤肉的搭配，我完全同意：孜然真的很适合羊肉料理。
从现在起，每当我吃成吉思汗烤肉时，我决定总是用孜然给肉调味。"

---

## 转换特点

### 1. 汉字转换
汉字被转换为世界语词根：
- 我 → mi（我）
- 听 → aŭd（听）
- 很 → tre（非常）
- 良 → bon（好）

### 2. 上标识别符处理
当同一个汉字对应多个词根时，最常用的词根保留不带标记的汉字，其余用小型上标字母区分：
- 人 → hom（人类，无标记）
- 人ᴾ → person（个人）
- 人ᴼ → oni（一般的人们）
- 和ᴷ → kaj（和、与）
- 和ᴬ → akord（协调、契合）

### 3. 保留字母部分
已经用字母书写的部分保持不变：
- is, as, os → 动词时态词尾
- aj, oj, on → 名词·形容词格词尾
- kumino, jingisukan → 外来语或专有名词

### 4. 转换为小写
输出全部转换为小写（遵循世界语习惯）。

---

## 常见转换模式

| 汉字化 | 字母形式 | 含义 |
|--------|---------|------|
| 我 | mi | 我 |
| 你 | vi | 你 |
| 他 | li | 他 |
| 她 | ŝi | 她 |
| 和ᴷ | kaj | 和 |
| 是 | est | 是 |
| 有 | hav | 有 |
| 从 | de | 从 |
| 为 | por | 为了 |
| 共 | kun | 和...一起 |
| 内 | en | 在...里面 |
| 以 | per | 用 |

---

## 问题排查

### 有些汉字没有被转换
- 请检查CSV文件中是否有相应汉字的条目
- 请检查上标识别符是否正确输入（例如：人ᴾ、和ᴷ）

### 输出与预期不同
- 请检查输入文本中汉字和字母的分隔是否正确
- 请检查空格和标点符号的位置是否正确

---

## 高级示例

### 示例3：包含多种语法要素

**输入：**
```
昨 我 见is 美ajn 鸟ojn 内 la 园o, 和ᴷ 他们 唱is 很 甘e.
```

**输出：**
```
hieraŭ mi vidis belajn birdojn en la ĝardeno, kaj ili kantis tre dolĉe.
```

**中文翻译：**
"昨天，我在花园里看到了美丽的鸟儿，它们唱得很甜美。"

### 示例4：疑问句

**输入：**
```
何o 是as 你a 名o? 从 何e 你 来as?
```

**输出：**
```
kio estas via nomo? de kie vi venas?
```

**中文翻译：**
"你叫什么名字？你从哪里来？"

---

## 使用技巧

1. **保持空格**：汉字和字母之间要有适当的空格
2. **检查上标识别符**：确保上标字母（ᴬ、ᴷ、ᴾ、ᴼ 等）输入正确——在线编辑器（kanji-esperanto-monaco）输入词根时会自动带出正确形式
3. **测试小段文本**：先用短句测试，确认转换正确后再处理长文本
4. **保存结果**：使用下载功能保存转换后的文本

---

创建日期：2025年10月2日 / 全面更新：2026年8月22日
