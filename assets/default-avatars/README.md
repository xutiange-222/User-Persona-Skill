# 内置默认画像头像

skill 在未提供用户自定义头像时，按 **`<画像中文名>.png`** 从此目录匹配半身像。

## 解析优先级（渲染层）

1. `<项目运行目录>/画像头像素材/<文件名>.png` — 用户自定义（同名覆盖本目录）
2. `assets/default-avatars/<画像中文名>.png` — 本目录
3. 色块 + 首字占位 — 两处均无匹配文件时

## 维护

- **初始来源**：`docs/reference/reports/B-多角色/2B-DevOps五角色/assets/画像头像素材/`
- **同步脚本**：`python scripts/tools/sync_default_avatars.py`
- **样例裁切后刷新**：`python scripts/tools/build_sample_visuals.py` 会把 staging 里的头像合并回本目录

## 当前文件（约 14 张）

DevOps 五角色、Hi-Res 2C 五画像、电力调度四角色等样例报告所用头像名。新增画像若名称不在本目录，报告会显示占位，直到用户放入自定义图或维护人员补充默认 png。
