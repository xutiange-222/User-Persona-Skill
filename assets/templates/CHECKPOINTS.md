# 过程稿检查点清单

每完成一步必须落盘对应文件,**不得跳过**。续跑时先执行:

```bash
python scripts/recovery_check.py --workdir <本项目运行目录或过程稿目录> --format human
```

## 必交文件(按顺序)

| 步骤 | 文件 / 目录 | 说明 |
|------|-------------|------|
| 0 | `00-research-goal.json` | 研究目标(读者 / 问题 / 决策) |
| 1 | `01-paradigm.json` | 方式 A–E + toB/toC,含 `user_confirmed` |
| 2 | `02-classification.json` | **仅 R3/R4/R5** 需要 |
| 3 | `03-field-alignment.json` | 字段对齐,须通过 `validate_field_alignment.py` |
| 4 | `processed/*.txt` | 预处理后的访谈(每份一份) |
| 5 | `extracted/*.json` | 单文档抽取(份数 = processed 份数) |
| 6 | `04-personas.json` | 合并后的画像数据 |
| 7 | `05-report.json` | 渲染用组件 JSON(**禁止跳过**) |
| 8 | `../最终交付件-*/report.html` | 仅由 `render_report.py` 生成 |

## 重做某步

删除该步及之后的 JSON / 目录,再运行 `recovery_check.py` 查看 `next_step`。

## 禁止

- 直接手写 `report.html` 而不写 `05-report.json`
- 只有 `04-personas.json` 却没有 `extracted/` 逐份文件
- 只有 `alignment_mode` 而无完整字段池的 `03-field-alignment.json`
