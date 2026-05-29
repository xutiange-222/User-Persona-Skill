# user-persona skill V9 目录结构

见 `VERSION.md` 变更记录。渲染唯一入口: `scripts/components/render_report.py`。

```
user-persona-V9/
├── SKILL.md                    模型入口(九条硬约束 + 工作流)
├── 人类用户说明书.html          人类可读使用说明(浏览器打开)
├── VERSION.md                  版本变更
├── STRUCTURE.md                本文件
│
├── docs/reference/             非运行时参考(见 docs/reference/README.md)
│   ├── reports/                说明书用交付样例(按 A/B/D/E)
│   ├── layouts/                单页布局样板 + toB R4/R5 对照 HTML
│   ├── gallery/                组件 gallery
│   └── archive/                历史设计稿
│
├── paradigms/                  R1–R5 范式流程
├── steps/                      公共步骤
├── schemas/                    字段池 + 分类依据库
│
├── scripts/
│   ├── components/             ★ P8/P9 渲染核心
│   ├── tests/                  质量检查 + fixtures
│   └── tools/                  样例维护 + toB 布局样板生成
│
└── assets/
    ├── default-avatars/        ★ 内置默认画像头像(按 画像名.png 匹配)
    ├── prompts/
    ├── sample-sources/         样例图维护源(可选)
    └── templates/              _base.html + CSS
```

## 两类「参考/样例」分工

| 位置 | 用途 |
|------|------|
| `docs/reference/reports/` | 人类说明书 §3 链接的样例 + 维护脚本裁切源 |
| `docs/reference/layouts/` | 渲染前布局对照 HTML（含 toB R4/R5 样板） |

布局样板**再生成**：`scripts/tools/build_tob_r4_layout_sample.py`、`build_tob_r5_layout_sample.py` → 输出到 `docs/reference/layouts/`。

## 运行时输出(不在 skill 包内)

`用户画像报告输出/<项目名>-<时间>/` 含 `过程稿/`、`最终交付件-*` 等。

## 不应提交的中间物

- skill 根误跑的 `用户画像报告输出/`
- `docs/reference/layouts/_build/`(上述 build 脚本临时目录)
