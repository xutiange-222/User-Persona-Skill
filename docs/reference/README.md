# Visual references

本目录只保留人类说明书直接链接的五份完整参考报告。

参考报告统一读取 `assets/templates/` 的当前 CSS 和共享 HTML 骨架。刷新与校验命令：

```powershell
python scripts/tools/refresh_reference_reports.py
```

五份报告覆盖：

1. 2B 单画像
2. 2C 单画像
3. 2B 多角色、L1 总体旅程和 L2 单角色旅程
4. 2C 二维矩阵、画像、详情和旅程
5. 2C 多维分布、画像、详情和旅程

旧布局草稿、组件画廊、旧真值 HTML 和调试合成图不再作为参考入口。视觉契约以 `steps/visual-style-guide.md`、`assets/templates/_visual-system.json`、当前渲染脚本和五份完整参考报告为准。
