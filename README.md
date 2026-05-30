# User Persona Skill

中文 | [English](#english)

从用户访谈逐字稿生成结构化用户画像报告，产出可交互 HTML（后续将支持导出 PPT）。

本仓库是 **User Persona Skill** 的完整源码包，可安装到 **Claude Code** 或 **Cursor** 的 skills 目录。你提供访谈材料并说明研究目标后，Agent 会按固定工作流完成分类、字段对齐、抽取合并与渲染，最终交付一份可在浏览器中打开的画像报告。

**首次使用请优先阅读 [人类用户说明书（在线打开）](https://xutiange-222.github.io/User-Persona-Skill/%E4%BA%BA%E7%B1%BB%E7%94%A8%E6%88%B7%E8%AF%B4%E6%98%8E%E4%B9%A6.html)**，再查阅本 README 与 `SKILL.md`。（GitHub Pages 首次启用后约需 1–2 分钟生效。）

## 它适合什么问题

适合这类输入：

- 我有一批用户访谈，想整理成产品/设计能用的用户画像。
- 我知道有几类用户，想把访谈合并进已知角色里。
- 我不确定有几类用户，希望从访谈数据里聚类出画像。
- 我需要 toB（企业用户、开发者）或 toC（消费者）画像，并带证据原话可追溯。

不适合这类输入：

- 只有问卷统计、没有访谈原文，且不做定性归纳。
- 只要一页 PPT 草图，不需要结构化 HTML 报告与过程稿。
- 希望模型直接「凭感觉写画像」、不先对齐研究目标与字段。

这个 skill 需要你先说清楚 **报告给谁看、要回答什么问题、要支持什么决策**，越具体，画像越有针对性。

## 它会产出什么

运行后会在 skill 目录外生成项目文件夹（默认 `用户画像报告输出/<项目名>-<时间>/`），通常包含：

- **过程稿**：`00-research-goal.json`、`02-classification.json`、`03-field-alignment.json`、`04-personas.json`、`05-report.json` 等，可断点恢复。
- **最终交付件**：`最终交付件-*/report.html` — 单文件交互式 HTML，含画像页、矩阵/旅程等（视范式而定）。
- 可选：画像头像、典型场景截图（2B/2C 流程中会主动向你收集）。

五种构建方式（在 skill 内称方式 A–E，对应范式 R1–R5）：

| 方式 | 说明 |
|------|------|
| **A** | 单画像页 |
| **B** | 多角色 + 可选 L1/L2 旅程图 |
| **C** | 仅确定分类依据（准备步骤） |
| **D** | 二维矩阵（两个区分点，四象限画像） |
| **E** | 多维分布 |

报告强调 **全量证据原话**：每个观点可 hover 查看绑定的访谈引用，方便 UXR 复核，而不是只给二手归纳。

## 安装方式

**方式一：克隆本仓库**

```bash
git clone https://github.com/xutiange-222/User-Persona-Skill.git
```

将文件夹放到 skills 目录，并确保文件夹名为 `user-persona`（或与 `SKILL.md` 里 `name: user-persona` 一致）：

Windows：

```text
C:\Users\<你的用户名>\.claude\skills\user-persona\
```

macOS / Linux：

```text
~/.claude/skills/user-persona/
```

**方式二：下载 Release / 本地 zip**

若你持有 `user-persona.zip`，解压后同样放入上述 `skills` 目录。注意解压后应是 `skills/user-persona/SKILL.md`，不要多套一层目录。

安装后：

1. 重启 Claude Code / Cursor。
2. 询问 Agent 是否可以使用 `user-persona` skill。
3. 人类可读说明：[在线打开说明书](https://xutiange-222.github.io/User-Persona-Skill/%E4%BA%BA%E7%B1%BB%E7%94%A8%E6%88%B7%E8%AF%B4%E6%98%8E%E4%B9%A6.html)（或本地打开 `人类用户说明书.html`）。

## 使用示例

可以直接这样提问：

```text
我有一组电力调度员的访谈 txt，想给产品团队做 AI 辅助调度功能的画像，用二维矩阵区分两类岗位差异。
```

```text
这是 5 份 HiRes 音乐用户的访谈，想聚类出 3～4 个 toC 画像，报告给 UX 做专区改版。
```

Agent 会先与你对齐研究目标，再推荐方式 A–E 与 toB/toC，然后按步骤推进。不要跳过「研究目标」和「字段对齐」——这是九条硬约束里的最高优先级。

## 工作方式（概要）

典型流程：

1. **研究目标**：读者、研究问题、决策用途。
2. **范式选择**：A–E × toB/toC。
3. **预处理**：docx/txt/xlsx → 可抽取文本。
4. **分类 / 聚类**：已知角色合并或数据驱动分群。
5. **字段对齐**：确认每个画像展示哪些信息块、密度与组件。
6. **抽取与合并**：按人抽取，再按画像聚合，绑定 `evidence_quotes`。
7. **渲染**：`scripts/components/render_report.py` 生成 HTML，校验通过后再交付。

渲染 **不由模型直接写 HTML**，而是由 Python 组件根据 `05-report.json` 确定性生成。

## 参考样例

仓库内 `docs/reference/reports/` 提供可打开的完整 HTML 样例，例如：

- toB 单画像：`docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html`
- toB 多角色旅程：`docs/reference/reports/B-多角色/2B-DevOps五角色/report.html`
- toB 二维矩阵：`docs/reference/reports/D-二维矩阵/2B-电力调度员/report.html`
- toC 二维 / 多维：`docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` 等

详见 `docs/reference/README.md`。

## 限制

- 依赖访谈 **原文质量**；转写错误会进入证据链。
- 模型负责归纳，**你必须在字段对齐阶段** 控制信息量，否则网格组件会要求删减而非自动省略。
- 大项目需多轮对话；过程稿 JSON 是恢复与审计的关键。
- Python 3.10+；渲染与校验需在本地执行。

## 仓库结构（节选）

```text
user-persona/
├── SKILL.md                 # Agent 入口
├── 人类用户说明书.html
├── paradigms/               # R1–R5
├── steps/
├── schemas/
├── scripts/
│   ├── components/          # render_report.py
│   ├── tests/
│   └── tools/
├── assets/
└── docs/reference/          # 静态样例
```

运行时产出目录 `用户画像报告输出/` 不应提交进 skill 包（已在 `.gitignore`）。

当前版本：**V9**（见 `VERSION.md`）。

## 反馈方向

试用后欢迎反馈：

- 字段对齐与「放不下」时的协作体验是否顺畅。
- 证据 hover 是否足够支撑 UXR 复核。
- toB 旅程图 / toC 详情页的信息密度是否合理。
- HTML 报告在汇报场景是否好用。

---

## English

[中文](#user-persona-skill) | English

User Persona Skill turns user-interview transcripts into structured persona reports as interactive HTML.

This repository is the full **skill package** for **Claude Code** or **Cursor**. After you provide interview files and align on research goals, the agent follows a fixed workflow—classification, field alignment, extract/merge, and render—to deliver a browser-ready persona report.

**First-time users: start with the [human guide (open in browser)](https://xutiange-222.github.io/User-Persona-Skill/%E4%BA%BA%E7%B1%BB%E7%94%A8%E6%88%B7%E8%AF%B4%E6%98%8E%E4%B9%A6.html)** before this README or `SKILL.md`. (GitHub Pages may take 1–2 minutes after first enable.)

## What It Is For

Good fits:

- You have interview transcripts and need personas for product or UX.
- You already know user segments and want to merge interviews into defined roles.
- You need data-driven clustering to discover segments.
- You need **toB/toD** or **toC** personas with **traceable quote evidence**.

Poor fits:

- Only survey statistics, no qualitative transcripts.
- A one-off slide sketch without structured HTML and process artifacts.
- Skipping research-goal alignment and letting the model guess what matters.

State **who will read the report, what questions it must answer, and what decisions it supports**—the skill anchors everything on that.

## What It Produces

Output lives outside the skill folder (default: `用户画像报告输出/<project>-<timestamp>/`):

- **Process artifacts**: JSON checkpoints (`00-research-goal.json`, `04-personas.json`, `05-report.json`, …) for recovery.
- **Delivery**: `report.html` — self-contained interactive HTML (matrix, journeys, etc. depending on paradigm).

Five build modes (**A–E**, mapped to paradigms **R1–R5**):

| Mode | Description |
|------|-------------|
| **A** | Single persona page |
| **B** | Multi-role + optional L1/L2 journey |
| **C** | Classification basis only (prep) |
| **D** | 2D matrix (two segmenting variables) |
| **E** | Multi-variable distribution |

Reports bind **full evidence quotes** per insight (hover to review), not cherry-picked examples only.

## Installation

**Option 1: Clone**

```bash
git clone https://github.com/xutiange-222/User-Persona-Skill.git
```

Place the folder in your skills directory as `user-persona`:

```text
~/.claude/skills/user-persona/          # macOS / Linux
C:\Users\<you>\.claude\skills\user-persona\   # Windows
```

**Option 2: Zip**

If you have `user-persona.zip`, extract so that `SKILL.md` sits directly under `skills/user-persona/`.

Then restart Claude Code / Cursor and confirm the agent can use the `user-persona` skill. Human guide: [open online](https://xutiange-222.github.io/User-Persona-Skill/%E4%BA%BA%E7%B1%BB%E7%94%A8%E6%88%B7%E8%AF%B4%E6%98%8E%E4%B9%A6.html).

## Example Prompts

```text
I have power-dispatch operator interview transcripts and need a 2D matrix persona report for an AI-assisted dispatch feature.
```

```text
Five HiRes music user interviews—cluster into 3–4 toC personas for a product zone redesign.
```

The agent will align research goals first, then recommend mode A–E and toB/toC.

## Workflow (Summary)

1. Research goals (audience, questions, decisions).
2. Paradigm A–E × toB/toC.
3. Preprocess docx/txt/xlsx.
4. Classify or cluster.
5. Field alignment (blocks, density, components).
6. Extract per respondent, merge per persona with `evidence_quotes`.
7. Render via `scripts/components/render_report.py` + validators.

HTML is **not** written free-form by the model; rendering is deterministic from JSON.

## Reference Samples

Under `docs/reference/reports/`, e.g.:

- toB single: `A-单画像/2B-保障型运维工程师/report.html`
- toB multi-role journey: `B-多角色/2B-DevOps五角色/report.html`
- toB 2D matrix: `D-二维矩阵/2B-电力调度员/report.html`

See `docs/reference/README.md`.

## Limitations

- Output quality depends on transcript fidelity.
- Field alignment controls density; components will not silently drop items.
- Multi-turn sessions; keep process JSON for audit/recovery.
- Requires Python 3.10+ locally.

## Repository Layout (Excerpt)

```text
user-persona/
├── SKILL.md
├── paradigms/
├── steps/
├── schemas/
├── scripts/components/   # render_report.py
├── assets/
└── docs/reference/
```

Version **V9** — see `VERSION.md`.

## Feedback

We welcome input on field-alignment UX, evidence traceability, journey/detail density, and report usability in stakeholder reviews.

Maintained by [@xutiange-222](https://github.com/xutiange-222).
