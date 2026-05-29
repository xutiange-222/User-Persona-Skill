# 布局样板（layouts）

单页或局部 HTML，供 `steps/visual-system.md` 渲染前对照。**不是完整交付包**——不含多 tab 全量数据，只验证某一 layout 的视觉骨架。

| 文件 | layout | 用途 |
|------|--------|------|
| `2B-电力调度员-双页.html` | layout-2b-grid × 2 | 画像核心 vs 工作细节双页 |
| `2B-电力调度员-多tab.html` | layout-2b-grid × N | 多 persona tab |
| `2B-R4矩阵-样板.html` | matrix + 2b-grid + L2 | toB R4 最小结构 |
| `2B-R5多维-样板.html` | distribution + 2b-grid + L2 | toB R5 最小结构 |
| `2C-品质聆听者-单页.html` | layout-2c-portrait | toC 单画像拼贴 |
| `2C-品质聆听者-双页.html` | 2c-portrait + 2c-detail | toC 主画像 + 专题详情 |

CSS 使用本目录 `_design-tokens.css`、`_components.css`（与 `assets/templates/` 同步副本）。

完整多 tab / 旅程样例见 `../reports/`。重新生成 toB R4/R5 样板：

```bash
python scripts/tools/build_tob_r4_layout_sample.py
python scripts/tools/build_tob_r5_layout_sample.py
```
