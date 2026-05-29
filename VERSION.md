# user-persona V9

**V8 未修改**。V9 为结构重构版。

## 版本

- 基线: user-persona-v8 (P8 组件化)
- 第二轮: 2026-05-29 — skill 级收口
- 第三轮: 2026-05-29 — 低风险同步与文档对齐
- 第四轮: 2026-05-29 — 用户素材必问流程(头像 + 典型场景截图,2B/2C)
- 第五轮: 2026-05-29 — 电力调度员复盘收口(R4×toB 路由、旅程校验、模板 CSS)
- 第六轮: 2026-05-29 — 5 范式 × 2B/2C 路由收口
- 第七轮: 2026-05-29 — 交付包收口(删说明书 V2、清理 skill 内误跑中间物)
- 第八轮: 2026-05-29 — `docs/reference/` 四类重组(reports / layouts / gallery / archive)
- 第九轮: 2026-05-29 — `examples/` 只留交付件；构建脚本并入 `scripts/tools/`

## 第九轮变更

- **examples/**：删除全部 `过程稿/`；扁平为 3 个最终交付件目录；去掉 `project-runs/` 嵌套
- **删除** skill 根 `过程稿/examples/` → 迁入 `scripts/tools/build_tob_r4_layout_sample.py`、`build_tob_r5_layout_sample.py`
- **说明**：原 `回归测试/toB-*.html` 已在第八轮并入 `docs/reference/layouts/`（无独立 `回归测试/` 目录）

## 第八轮变更

- **重组** `docs/reference/`：`reports/`(按 A/B/D/E 交付样例)、`layouts/`(单页布局样板)、`gallery/`、`archive/`
- **合并** 原 `回归测试/` 布局文件入 `docs/reference/layouts/`；删除 skill 根 `回归测试/`
- **统一** 人类说明书样例链接 → `docs/reference/reports/`；visual-system / field-alignment 路径同步
- **更新** 维护脚本路径(build_gallery、build_sample_visuals、toB-R4/R5-build_report)

## 第七轮变更

- **删除** `说明书-V2.html`；`说明书.html` 为唯一人类说明书
- **删除** skill 根目录 `用户画像报告输出/`(电力调度员误跑产出；交付样例已在 `docs/reference/说明书-样例/`)
- **删除** `回归测试/_toB-*-minimal-build/`(可由 `过程稿/examples/*.py` 再生成)
- **删除** `docs/电力调度员-问题总结与修改说明.md`、`assets/templates/archive/`、examples 内 `processed/` 访谈原文与问题说明
- **更新** `STRUCTURE.md`、`.gitignore`；样例图维护源改为 `assets/sample-sources/`

## 第六轮变更

- **主路由表**: SKILL / visual-system / field-alignment — 方式 A–E × research_type 完整对照
- **范式**: R1–R5 均补「按 research_type 选族」; R5 新增 toB 渲染专节
- **话术**: toB 初判支持 D/E; classify-basis-tob 明确「默认 R3、确认后可用 D/E」
- **校验**: `P8-OVERVIEW-FORBIDDEN-COMPONENT`(R4/R5 总览禁画像/旅程组件)
- **REGISTRY/CSS**: R4/R5 总览 theme-neutral 说明; 矩阵/分布 CSS 注释修正
- **回归**: `回归测试/toB-R5-多维分布-样板.html`、`过程稿/examples/toB-R5-build_report.py`
- **2C mockup**: 专题详情 `mockup_list` 统一帧高 `--mockup-frame-height`,真图 `object-fit:contain` 等高缩放宽

## 第五轮变更

- **校验**: `P8-JOURNEY-CELLS-SHAPE`(journey_2c 维度×阶段轴向)、`P8-THEME-LAYOUT-MISMATCH`(theme 与 layout/component 族一致)
- **路由**: R4/R5 子页按 `research_type` 分支(toB → 2b-grid + tob_journey_l2; toC → 2c-portrait + journey_2c)
- **文档**: SKILL / visual-system / field-alignment / R4-2d-matrix / render-persona-page / REGISTRY 同步
- **CSS**: mockup 真图改为 `width:100%; height:auto`（取消 absolute+9:14 cover，修复半屏/重影）；grid `min-width:0` 保留
- **回归**: `回归测试/toB-电力调度员-R4矩阵-样板.html`、`过程稿/examples/toB-R4-build_report.py`
- **项目**: 电力调度员交付件改为 `theme=2b` + toB 组件集

## 第四轮变更

- **新增** `steps/visual-assets.md` — 三处检查点(字段对齐 / 渲染前 / 交付后)
- **约束 15**: SKILL 硬规则 — 必须主动问头像与典型场景截图
- **更新** field-alignment、visual-system、render-persona-page、paradigms、schema-tob/toc
- **修正** visual-system 2C detail「不接收用户截图」与 mockup_list 实现的矛盾

## 第三轮变更

- **修复**: `reduce_field.py` 中 `fault_scenarios` / `high_freq_tasks` prompt 映射至 `reduce_titled_list.txt`
- **文档**: SKILL / paradigms / schemas / steps / REGISTRY / CONTRACTS 统一 24 组件口径; `task_freq_list` → `titled_list`
- **收尾**: 清理 `_reports` 缓存; 新增 `docs/reference/README.md`、根 `.gitignore`

## 第二轮变更

### 组件层(第一轮)

- `assemble.py` → `layout_rules.py` + `grid_module.py` + 瘦 `assemble.py`
- 删除 `shared.py`; `render_nav_trio` → `nav.py`
- `_utils.render_illust()` / `render_avatar()`
- `components/validate.py` + CLI 兼容包装
- 20 smoke tests → `test_renderers_smoke.py`

### Skill 级(第二轮)

- **删除 P7**: `render_html.py`, `render_matrix.py`, `render_multivariable.py`, `layout.py`
- **删除遗留**: `assets/templates/report.html`, `reduce_fault_list.txt`, `reduce_task_freq.txt`
- **2C renderer 合并**: `toc_portrait.py` + `toc_detail.py` → `toc.py`
- **测试合并**: `test_matrix_2d` + `test_matrix_attrs` → `test_matrix.py`
- **证据测试迁出**: `test_evidence_duplication` → `scripts/tests/`
- **样例迁出**: `用户画像报告输出/` → `examples/project-runs/`
- **参考迁出**: `真值草稿-demo.html` → `docs/reference/`
- **文档统一**: paradigms/steps/visual-system 只写 `render_report.py` 单路径
- **契约检查**: `check_skill_contracts` 检 P8 入口而非 render_html

## 未做(P3)

- REGISTRY.md 拆分瘦身(仍 1200+ 行)
- scenario/ai + generic 三 schema 合并
- `gallery_data.json` 按 layout 拆分
- `_components.css` 按 layout 拆 partial

## 验证

```bash
cd user-persona-V9
python -m pytest scripts/components/tests/ scripts/tests/test_evidence_duplication.py -q
python scripts/tests/check_skill_contracts.py
```
