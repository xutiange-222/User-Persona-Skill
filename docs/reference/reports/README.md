# 交付样例（reports）

完整可打开的 `report.html` 包，按**构建方式**组织。每个子目录自包含 `report.html`、CSS 与 `assets/`。

| 路径 | 方式 | 说明 |
|------|------|------|
| `A-单画像/2B-保障型运维工程师/` | A | DevOps 多角色报告裁切 · 主画像 + 细节 + 旅程 |
| `A-单画像/2C-内行场景派/` | A | HiRes 2维报告裁切 · 主页 + 专题 + 旅程 |
| `B-多角色/2B-DevOps五角色/` | B | 五角色 tab + L1 整体旅程 + 各 L2 |
| `D-二维矩阵/2B-电力调度员/` | D | toB 四象限 + 画像 + L2 旅程 |
| `D-二维矩阵/2C-HiRes-2维/` | D | toC 矩阵首页 + 五类画像 + 旅程 |
| `E-多维分布/2C-HiRes-多区分点/` | E | toC 多维分布 + 五类画像 + 旅程 |

## 维护（避免 HTML/CSS 版本漂移）

**改模板 CSS 或 renderer 后**，不要手改样例 HTML，应跑：

```bash
python scripts/tools/refresh_reference_reports.py
```

该脚本会：

1. 用 v8 `05-report.json` 重渲染 `D-二维矩阵/2C-HiRes-2维`
2. 从 v8 多维交付件同步 `E-多维分布/2C-HiRes-多区分点` 的 distribution 页
3. 同步 `assets/templates/_*.css` 到各样例目录
4. 生成/裁切 `assets/`（头像 + HiRes 界面截图）并 patch HTML 引用
5. 重裁切 A 单画像样例（`build_single_persona_samples.py`）
6. 同步 2C 专题页 mockup 结构与截图（`sync_reference_reports.py`）

单独步骤：

| 脚本 | 何时用 |
|------|--------|
| `build_single_persona_samples.py` | 只改 D/E 全量报告、需更新 A 裁切 |
| `build_sample_visuals.py` | 只换头像/截图源图或重建 assets |
| `sync_reference_reports.py` | 只改模板 CSS 或 2C mockup 结构 |
