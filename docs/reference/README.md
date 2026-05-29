# 参考材料（非运行时）

本目录存放 skill 开发与验收用的**静态参考**，不参与 `render_report.py` 流水线。

## 目录结构

```
docs/reference/
├── reports/     完整可打开的交付样例（人类说明书 §3 链到这里）
├── layouts/     单页布局样板（渲染前视觉对照，见 visual-system.md）
├── gallery/     组件 gallery（golden vs renderer 并排对比）
└── archive/     历史设计稿，仅供回溯
```

## 快速索引

| 构建方式 | 2B/2D 样例 | 2C 样例 |
|---------|-----------|---------|
| **A 单画像** | [保障型运维工程师](reports/A-单画像/2B-保障型运维工程师/report.html) | [内行场景派](reports/A-单画像/2C-内行场景派/report.html) |
| **B 多角色** | [DevOps 五角色 + L1/L2 旅程](reports/B-多角色/2B-DevOps五角色/report.html) | — |
| **D 二维矩阵** | [电力调度员 R4](reports/D-二维矩阵/2B-电力调度员/report.html) | [HiRes 2维](reports/D-二维矩阵/2C-HiRes-2维/report.html) |
| **E 多维分布** | 见 `layouts/2B-R5多维-样板.html` | [HiRes 多区分点](reports/E-多维分布/2C-HiRes-多区分点/report.html) |

运行时新项目的默认输出目录仍为 **`用户画像报告输出/`**（见 `SKILL.md`），与本目录无关。

## 维护脚本

```bash
# 一键刷新六份说明书样例（重渲染 + CSS + assets + A 裁切）
python scripts/tools/refresh_reference_reports.py

# 方式 A 单画像裁切（仅改 D/E 源报告后）
python scripts/tools/build_single_persona_samples.py

# 样例头像 / 截图写入 reports（改 assets/sample-sources/ 后）
python scripts/tools/build_sample_visuals.py

# 模板 CSS + 已裁切截图 + 2C 专题页结构 → reports（改模板或 A-单画像/2C assets 后）
python scripts/tools/sync_reference_reports.py

# L2 单角色旅程：菱形须为问句判断 + 是/否 分支，痛点只在 focuses 行（见 REGISTRY §3.0.2）
python scripts/tools/refresh_l2_uml_in_reports.py
# 从 05-report.json 全量重渲染（含证据引号）见 render_report.py

# 组件 gallery 重新生成
python scripts/components/tests/build_gallery.py

# toB R4/R5 布局样板重新生成
python scripts/tools/build_tob_r4_layout_sample.py
python scripts/tools/build_tob_r5_layout_sample.py
```
