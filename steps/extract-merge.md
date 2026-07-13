# 抽取与归并

本阶段把已确认范围内的每份资料独立抽取，再按字段归并。归并结果先写入 `04-personas.draft.json`，随后由官方脚本生成中文 `04-personas.md`。用户确认后封存为 `04-personas.json`。

## 进入条件

- `00` 至 `03` 的 MD/JSON 已配对并通过校验。
- `02-classification.json` 已包含用户确认的分组，或状态为 `not_applicable`。
- `03-field-alignment.json` 已固化字段清单、研究类型、素材选择和旅程范围。
- 输入范围已经记录在 `00-research-goal.json`。

## 第一步：逐份预处理

```powershell
python scripts/preprocess.py --input-dir <输入目录> --workdir <项目目录>\过程稿
```

要求：

- 每个输入文件在 `processed/` 中有且只有一个对应文本。
- 文件名保持稳定，便于证据回溯。
- 预处理失败的文件必须显式记录，禁止静默跳过。
- 运行后用 `workflow.py status` 核对输入数和 processed 数。

预处理后立即运行 `build_source_manifest.py`。审核后必须满足：

- 相同内容只保留一个 source_id，物理重复文件从 processed/extracted 移除。
- 核心受访者标为 `primary`；背景材料、FAE 汇总或旁证标为 `supplemental`，并填写允许补充的字段。
- `unique_primary_interviews` 是报告中唯一可称为“访谈数”的值。
- `unique_supplemental_sources` 和 `analysis_assignment_count` 单独报告。
- 术语审计 Markdown 属于权威 reference，不进入 processed，不计访谈数；用 `build_terminology_glossary.py` 编译。

## 第二步：逐份独立抽取

```powershell
python scripts/extract_single.py --input <processed文件> --output <相同相对路径的extracted文件.json> --fields '<03确认的字段JSON>' --persona-type <toB或toC或toD>
```

运行时使用：

- 公共语言契约：`assets/prompts/_shared-language-contract.txt`
- 抽取 prompt：`assets/prompts/extract_single.txt`
- 字段定义：`--fields` 传入的已确认字段清单

要求：

- 一份输入对应一份 extracted JSON，保留 `processed/` 下的分组相对路径。
- 每份抽取只读取当前输入，禁止借用其他受访者信息。
- 每条证据保留 source 和逐字原话。
- source 使用抽取脚本生成的稳定匿名 `_source_id`，原文件名只留在内部 `_source_file`。
- 未提及字段按 prompt 约定输出缺失状态，禁止补写合理猜测。
- 每份输出立即落盘，禁止把多份结果只留在上下文中。
- 默认按约 12k 输入 token 分段，模型上下文更小时使用 `--max-input-tokens` 下调，禁止把整份长访谈硬塞进一次调用。

## 第三步：按字段归并

```powershell
python scripts/reduce_field.py --field <字段名> --inputs <同组全部extracted JSON> --output <过程稿目录>\reduced\<画像ID>\<字段名>.json
```

`reduce_field.py` 按字段选择固定 prompt：

| 字段类型 | prompt |
|---|---|
| 基本资料 | `reduce_basic_profile.txt` |
| 职责占比 | `reduce_responsibilities.txt` |
| 协作关系 | `reduce_collaboration.txt` |
| 场景列表 | `reduce_scenario_list.txt` |
| 系统列表 | `reduce_system_list.txt` |
| 标题加说明列表 | `reduce_titled_list.txt` |
| 普通字符串列表 | `reduce_string_list.txt` |
| 一句话需求 | `reduce_one_sentence.txt` |
| 代表原声 | `reduce_quotes.txt` |
| 自定义字段 | `reduce_generic.txt` |

归并要求：

- `mention_count`、`mentioned_by`、`evidence_quotes` 三者严格一致。
- 同一受访者在同一归并项中最多计数一次。
- 原话不能改写，来源不能脱落。
- 每条原话必须直接支撑当前结论。同一证据包完整复用于三个以上结论，或同一句原话支撑六个以上结论，会被视为机械复用并阻塞。
- 冲突、少数观点和证据不足要显式保留。
- 每个字段单独写文件，字段失败时只重跑该字段。
- `reduced/` 只保存逐字段归并结果，禁止把归并结果混入一一配对的 `extracted/`。
- `mention_count` 的分子和分母只计算 primary。supplemental 只补其 `supplemented_fields`，不能单独形成核心结论。

## 第四步：组装并确认画像

1. 汇总同一画像的字段归并结果。
2. 生成 `04-personas.draft.json`，再运行 `python scripts/workflow.py --workdir <过程稿> prepare-04 --stem 04-personas`。MD 字段标题必须使用 `03-field-alignment.json.fields_display_names` 中的中文名称。常用字段由脚本映射为中文。
   `prepare-04` 会自动把每个画像的完整字段写入 `reduced/persona-N.json` 聚合快照。弱模型无需手工创建每字段一个文件；已有逐字段归并文件仍兼容。
3. 停止并等待用户确认。
4. 用户调整后更新 MD，再次确认。
5. 为 03 的每个字段写 `field_decisions`：`full`、`condensed` 或 `omitted`。压缩与省略必须写原因和具体信息损失，并在 04 MD 展示给用户。
6. 把所有最终展示模块完整写入 `04-personas.json.personas[].display_components`。这是报告正文唯一真值。
7. 用户确认后运行封存脚本。脚本核对草稿与 MD 的内容指纹，再生成 `04-personas.json`。
8. 运行 `python scripts/validate.py --input <过程稿目录>\04-personas.json`。

禁止调用通用多数表决脚本直接生成画像。字段语义聚类由固定 reduce prompt 完成，用户拥有最终确认权。

## 第五步：隐私与完整性检查

```powershell
python scripts/privacy_guard.py --workdir <过程稿目录>
python scripts/workflow.py --workdir <过程稿目录> status
```

进入旅程确认前必须满足：

- 输入、processed、extracted 数量一致。
- 每个画像的成员都来自 02 的确认映射。
- 画像 MD/JSON 已配对。
- 证据来源可以回到单份 extracted 文件。
- `source-manifest.json` 的哈希、层级、字段授权和三类计数通过校验。
- 每个 `display_components` 的 props 通过对应组件 schema。
- 03 选中的全部字段都存在于 `fields` 和 `field_decisions`；`full`、`condensed` 字段进入 `source_fields`，`omitted` 字段不进入组件。
- 展示层不含真实姓名、电话、邮箱、账号或未授权组织信息。

## 模型接口配置

`extract_single.py` 和 `reduce_field.py` 读取：

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`

调用失败时保留已有中间文件，修复配置后从缺失的单份抽取或单字段归并继续。
