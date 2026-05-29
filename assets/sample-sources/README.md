# 样例图维护源（可选）

本目录供 `scripts/tools/build_sample_visuals.py` 重新裁切说明书样例头像/截图时使用。

- `2B*.png` — 2B 头像合成图（3×2 网格，取 5 格给 DevOps；左下第 6 格给电力调度员）
- `2C*头像*.png` — 2C 头像条（2×2 四格；第 5 个 persona 暂用 2B 第 6 格补位，可另提供 `2C*5*` 源图）
- `2C*手机*.png` / `2C*截图*.png` — HiRes 五屏横拼截图源

**若目录为空或缺文件**，`build_sample_visuals.py` 会自动生成占位合成条（彩色头像 + 示意 UI 截图），足够说明书样例展示；有真实合成图时可覆盖同名文件后重跑。

**正常运行 skill 不需要此目录**；`docs/reference/reports/` 内样例应自带 `assets/`。

一键刷新全部 6 份样例：

```bash
python scripts/tools/refresh_reference_reports.py
```
