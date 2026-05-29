# 范式 R1:文件已分组(方式 B)

**用户场景**:用户已经把不同角色的访谈分文件夹放好,或文件名前缀清晰体现了角色。

**适用**:toB / toD / toC 都可以。

---

## 前置条件

- `00-research-goal.json` 已确认
- `01-paradigm.json` 已确认范式 = R1,并记录了**分组信息**:

```json
{
  "version": "v8",
  "paradigm": "R1",
  "research_type": "toB",
  "groups": [
    {
      "name": "调度员",
      "members": ["邓老师", "孔老师", "肖老师"]
    },
    {
      "name": "运维",
      "members": ["刘老师", "碳中和老师"]
    }
  ]
}
```

分组信息由模型基于文件夹结构或文件名自动识别,并和用户确认。

---

## 流程概览

```
Step 0: 识别分组       → 模型基于文件夹/文件名,产物 01-paradigm.json
Step 1: 字段对齐       → 引用 steps/field-alignment.md
Step 2: 单文档抽取(map) → 引用 steps/extract-merge.md(对每位受访者跑一遍)
Step 3: 多份合并(reduce) → 引用 steps/extract-merge.md(每个画像独立 reduce)
Step 4: 渲染           → 引用 steps/render-persona-page.md(多画像 tab 切换)
```

R1 比 R2 多的就是:**分组识别 + 多画像分别 reduce + 多画像渲染**。

---

## Step 0:识别分组

模型读 `processed/` 下的所有文件,基于:
- 文件夹结构(如 `processed/调度员/张三.txt`)
- 文件名前缀(如 `processed/调度员_张三.txt`)

形成初步分组,**和用户确认**:

```
我从文件结构识别出 2 个分组:

【调度员组】(3 位):邓老师、孔老师、肖老师
【运维组】(2 位):刘老师、碳中和老师

这个分组对吗?
- 对,继续
- 调整某位受访者的归属
- 重新分组
```

用户拍板后写入 `01-paradigm.json`。

---

## Step 1:字段对齐

执行 `steps/field-alignment.md`。

**R1 专属**:多个画像可以共用字段集,也可以各自不同。

默认所有画像用同一套字段。如果用户要不同画像选不同字段,模型主动问:

```
你的两个画像【调度员】和【运维】,字段要不要不同?
- 用同一套(推荐,便于对比)
- 不同画像选不同字段(每个画像我单独问一次)
```

---

## Step 2:单文档抽取

调用 `scripts/extract_single.py`。

对所有受访者执行一次抽取(无论属于哪个分组,抽取的字段是一样的)。

产物 `extracted/{受访者名}.json`。

---

## Step 3:多份合并

调用 `scripts/reduce_field.py`。

**R1 专属**:每个画像**独立 reduce**。例:【调度员】组的 pain_points reduce 时,只合并邓老师、孔老师、肖老师的数据;【运维】组的 pain_points 只合并刘老师、碳中和老师的数据。

产物 `04-personas.json` 结构:

```json
{
  "version": "v8",
  "paradigm": "R1",
  "personas": [
    {
      "name": "调度员",
      "members": ["邓老师", "孔老师", "肖老师"],
      "fields": { ... }
    },
    {
      "name": "运维",
      "members": ["刘老师", "碳中和老师"],
      "fields": { ... }
    }
  ]
}
```

---

## Step 3.5:用户素材确认(渲染前必做)

字段对齐 Step 5.0 须已按 `steps/visual-assets.md` 问过用户。写 `05-report.json` 前执行**检查点 B**(扫描目录、确认映射);交付时执行**检查点 C**。2B 画像须覆盖头像 + `scenario_grid` 典型场景截图意愿。

---

## Step 4:渲染

调用 `scripts/components/render_report.py`,读取 `过程稿/05-report.json`,使用统一 16:9 骨架 `assets/templates/_base.html`、`_design-tokens.css`、`_components.css`。

报告顶部一个 tab 导航:
```
[调度员] [运维]
```

点击切换显示对应画像。

详细规则见 `steps/render-persona-page.md`。

## 渲染:按 research_type 选族

多 tab 导航;每个画像子页按 `research_type` 分支(见 `SKILL.md` §布局自动判断 主路由表 · 方式 B):

| research_type | 画像子页 | 旅程(用户确认时) |
|---------------|----------|------------------|
| toB / toD | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` + `tob_journey_l2`(可选 L1) |
| toC | `layout-2c-portrait`(溢出→`layout-2c-detail`) | `layout-2c-journey` + `journey_2c` |

---

## 用户对话样例

```
模型:
你的研究是 toB,方式 B(文件已分组)。
我从文件结构识别出 2 个分组:【调度员】3 位,【运维】2 位。
这个分组对吗?

用户:
对。

模型:
好,基于研究目标(给产品团队看,回答 AI 辅助决策需求),
我推荐以下字段(★ 是推荐的):
[展示字段池]

两个画像要用同一套字段吗?
- 用同一套(推荐)
- 不同画像选不同字段

用户:
用同一套,按推荐来。

模型:
[按 steps/visual-assets.md 检查点 A 询问头像与典型场景截图;记录 visual_assets]
[若用户要补图:渲染前再执行检查点 B]

[执行 extract + reduce + render]

报告已生成。包含两个画像【调度员】【运维】,顶部可切换。
[按检查点 C 说明头像/场景图使用或占位情况]
```

---

## 边界情况

- **某分组只有 1 位受访者**:照样独立成画像,提示"该分组样本只有 1 人,内容可能单薄"
- **文件结构不一致(部分有文件夹,部分平铺)**:模型如实展示识别出的分组,把"位置不明确"的文件让用户决定归属
- **用户在确认分组时想换范式(比如发现其实文件分错了,想走 R3 重新分类)**:删 `01-paradigm.json`,重启 skill 重选范式
- **某画像最终用户不满意**:可以单独修改该画像的字段或受访者归属,重新跑 reduce(只跑该画像的字段,不影响其他画像)

---

## 最终产出格式(P8 组件化,2026-05-25 起强制)

不允许直接产 HTML 字符串。必须产符合 `scripts/components/schemas/report.json` 的 components JSON,存到 `过程稿/05-report.json`。

**LLM 决策**:
1. 完成 `04-personas.json` 后,按 `steps/visual-system.md` §2 选定每个 persona 的 `layout`
2. 按 `scripts/components/REGISTRY.md` §9.2 的 24 个组件 type,挑出本画像需要的组件并按重要性排序
3. 每个组件的 `props` 严格匹配 `scripts/components/schemas/<type>.json`
4. 写出 `05-report.json`(顶层结构见 `schemas/report.json`)

**渲染调用**:

```bash
python scripts/components/render_report.py     --input "过程稿/05-report.json"     --output "最终交付件-<目录>/report.html"
```

该脚本自动跑:事前 schema 校验(validate_components_json)+ layout 拼装(8 个 assemble 函数)+ CSS 随包 + 事后 HTML 体检(validate_html)。

**禁止**:
- 直接产 HTML 字符串(不要 cat <<EOF > report.html)
- 用 Edit 工具改最终 report.html(改源 JSON 重跑)
- 自创 component type 或 layout 名(只能从 24 type + 8 layout 里挑)
- 在 props 里塞 schema 之外的字段(`additionalProperties: false` 会拒)
- 写 SVG path / Unicode emoji 字符 / inline 几何 var(由 Python 渲染层算,见 SKILL.md 约束 13)

校验失败 → 看 ERROR 的 path 和 code 改 `05-report.json`,不要改 HTML 打补丁。
