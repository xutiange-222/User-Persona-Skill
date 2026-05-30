# User Persona Skill / 用户画像 Skill

**Bilingual Cursor Agent skill** that turns user-interview transcripts into structured persona reports — interactive HTML (exportable to PPT).

**面向 Cursor 的双语 Agent Skill**：从用户访谈逐字稿生成结构化用户画像报告，产出可交互 HTML（可导出 PPT）。

---

## What it does / 能做什么

| | English | 中文 |
|---|---------|------|
| **Input** | Interview transcripts (`.docx` / `.txt` / `.xlsx`) | 访谈逐字稿（docx / txt / xlsx） |
| **Output** | Structured persona report as self-contained HTML | 结构化画像报告（单文件 HTML） |
| **Audience types** | **toB / toD** (enterprise, developers) and **toC** (consumers) | 企业/开发者画像与消费者画像 |
| **Workflow** | Merge known roles **or** cluster unknown segments from data | 合并已知角色，或从数据聚类未知角色 |
| **Evidence** | Full quote traceability per insight (UXR-friendly) | 每个观点绑定全量原话证据，便于 UXR 复核 |

---

## Paradigms (A–E) / 五种构建方式

| Code | English | 中文 |
|------|---------|------|
| **A** | Single persona page | 单画像页 |
| **B** | Multi-role + optional L1/L2 journey | 多角色 + 可选旅程图 |
| **C** | Classification basis only (prep step) | 仅分类依据（准备步骤） |
| **D** | 2D matrix (two segmenting variables) | 二维矩阵（两个区分点） |
| **E** | Multi-variable distribution | 多维分布 |

Implementation flows live under `paradigms/R1–R5.md`. Sample deliverables: `docs/reference/reports/`.

---

## Quick start / 快速开始

### 1. Install as a Cursor skill / 安装为 Cursor Skill

Copy this repo into your Claude/Cursor skills folder, for example:

```text
~/.claude/skills/user-persona/
```

On Windows:

```text
C:\Users\<you>\.claude\skills\user-persona\
```

The agent entry point is **`SKILL.md`**. Human-readable guide (browser): **`人类用户说明书.html`**.

### 2. Run a project / 跑一个项目

1. Open Cursor and mention **用户画像**, **persona**, or **访谈分析** — the agent should load this skill.
2. Provide interview files and align the **research goal** first (audience, research questions, decisions to support).
3. Choose paradigm **A–E** and **toB / toC**.
4. Follow the skill workflow: preprocess → classify → field alignment → extract/merge → render.
5. Deliverables are written under **`用户画像报告输出/<project>-<timestamp>/`** (not inside the skill package).

### 3. Render entry point (developers) / 渲染入口（开发）

```bash
python scripts/components/render_report.py \
  --input <path-to>/05-report.json \
  --output <path-to>/report.html \
  --project-dir <project-root>
```

Quality checks:

```bash
python scripts/tests/run_quality_checks.py
```

---

## Core principles / 核心原则（九条硬约束摘要）

1. **Anchor on research goals** before deciding what matters — not data-driven guessing.  
   **先对齐研究目标**，再判断重要性。
2. **Do not choose for the user** — ask sharper questions instead.  
   **不替用户做选择**，只把问题问准。
3. **No silent truncation** in the UI; overflow goes back to field alignment.  
   **渲染层不静默截断**，放不下就回到字段对齐。
4. **User-facing language only** — no grid/json jargon in decisions.  
   **对用户屏蔽实现细节**。
5. **Full evidence quotes** per component — no “representative example only”.  
   **证据全量绑定**，不举例糊弄。
6. **Strict dimension boundaries** — clarify “classification basis” vs “profile fields”.  
   **维度边界清晰**。
7. **Deterministic rendering** — Python components, not model-written HTML.  
   **渲染确定性**（Python 组件化）。
8. **Schema + validator gates** before delivery.  
   **Schema 与校验器守门**。
9. **Recovery checkpoints** via `过程稿/` JSON artifacts.  
   **过程稿可恢复**。

Details: `SKILL.md`.

---

## Repository layout / 目录结构

```text
user-persona/
├── SKILL.md                 # Agent entry (workflow + hard constraints)
├── 人类用户说明书.html       # Human guide (open in browser)
├── README.md                # This file
├── VERSION.md               # Changelog
├── STRUCTURE.md             # Directory map
├── paradigms/               # R1–R5 flows
├── steps/                   # Shared steps (research goal, field alignment, …)
├── schemas/                 # Field pools & classification libraries
├── scripts/
│   ├── components/          # ★ HTML render core (render_report.py)
│   ├── tests/               # Quality checks & fixtures
│   └── tools/               # Sample maintenance scripts
├── assets/                  # Templates, prompts, default avatars
└── docs/reference/          # Static samples (reports / layouts / gallery)
```

Runtime project output (gitignored): `用户画像报告输出/`.

---

## Reference samples / 参考样例

Open in a browser (paths relative to repo root):

| Type | toB example | toC example |
|------|-------------|-------------|
| A Single | `docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html` | `docs/reference/reports/A-单画像/2C-内行场景派/report.html` |
| B Multi-role | `docs/reference/reports/B-多角色/2B-DevOps五角色/report.html` | — |
| D 2D matrix | `docs/reference/reports/D-二维矩阵/2B-电力调度员/report.html` | `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` |
| E Multi-var | `docs/reference/layouts/2B-R5多维-样板.html` | `docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html` |

See `docs/reference/README.md` for maintenance commands.

---

## Version / 版本

Current package: **V9** (refactored from v8; see `VERSION.md`).

---

## Requirements / 环境要求

- **Python 3.10+** (rendering & validation)
- **Cursor** or **Claude Code** with Agent Skills support
- Optional: `pytest` for component tests under `scripts/components/tests/`

---

## Contributing / 贡献

Issues and PRs welcome. Please run `python scripts/tests/run_quality_checks.py` before submitting renderer or schema changes.

欢迎 Issue / PR。修改渲染或 Schema 前请跑质量检查脚本。

---

## License / 许可

Unless otherwise noted by the repository owner, all rights reserved. Add a `LICENSE` file if you intend to open-source under a specific terms.

如无另行说明，版权归仓库所有者所有；若需开源请自行添加 `LICENSE` 文件。

---

## Author / 作者

Maintained by [@xutiange-222](https://github.com/xutiange-222).
