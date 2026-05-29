# user-persona-v8 检查脚本使用说明

你平时只需要记住两条命令。

## 1. 检查 skill 本身

这是最常用的命令。它只检查 skill 源码、prompt、模板、路径和脚本契约,不需要你先生成画像报告。

```powershell
python "C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\skill_audit.py"
```

报告会生成在:

```text
C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\_reports\skill-audit-report.json
C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\_reports\skill-audit-report.md
```

优先看 `.md` 文件,它是中文报告。

## 2. 检查某次生成出来的画像产物

只有当你已经跑出一个画像项目后,才需要用这条。

```powershell
python "C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\artifact_audit.py" --workdir "你的项目运行目录"
```

项目运行目录通常长这样:

```text
D:\USER PERSONA BUILDING\用户画像报告输出\某项目名-20260520-203000
```

报告会生成在:

```text
C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\_reports\artifact-audit-report.json
C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\_reports\artifact-audit-report.md
```

## 什么时候用哪个

| 你的目的 | 运行哪个 |
|---|---|
| 检查 skill 写得稳不稳 | `skill_audit.py` |
| 检查 prompt / 模板 / 路径有没有明显问题 | `skill_audit.py` |
| 检查某个生成出来的 HTML 有没有问题 | `artifact_audit.py --workdir ...` |
| 检查某个 `04-personas.json` 的证据是否完整 | `artifact_audit.py --workdir ...` |

## 3. 组件代码守门(改完 schema / renderer / CSS 后跑)

P8 收尾轮新增了两个守门脚本,**改组件相关文件后顺手跑一次**,只输出 OK / 问题列表,几秒钟。

### 3.1 CSS 孤儿规则检查

扫 `_components.css` 里所有 class,检查是否还有 renderer 在产出。删过 renderer 又忘删 CSS,这里能拦住。

```powershell
python "C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\check_css_orphans.py"
```

输出 `OK: no orphan CSS classes found.` = 没问题。
若有列表,说明 CSS 有规则但 renderer 不再用 —— 看是不是该删,或者把名字加进脚本顶部的 `ALLOWLIST`(故意保留的、状态修饰、动态 f-string 拼接的)。

### 3.2 schemas / registry / report.json 三方对齐

新加或重命名组件时,检查 schema 文件、registry.py 注册、report.json 顶层 enum 三处是否一致。

```powershell
python "C:\Users\HUAWEI\.claude\skills\user-persona-v8\scripts\tests\check_three_way.py"
```

输出 `OK: N registry types, M schema files, K types in enum — all aligned.` = 没问题。
若失败,会告诉你具体是「registry 有 type 没 schema」还是「schema 有但 registry 没注册」还是「enum 没列」。

### 3.3 mojibake / XSS 守门

由 pytest 用例守护,跟主测试一起跑:

```powershell
cd "C:\Users\HUAWEI\.claude\skills\user-persona-v8"
python -m pytest scripts/components/tests/test_no_mojibake_literals.py scripts/components/tests/test_utils_security.py -q
```

`test_no_mojibake_literals` 防止源文件里再出现连续 `?` 乱码(Windows 编辑器编码事故);`test_utils_security` 防止 `escape_allow_strong` 退化成 XSS 漏洞。

## 不建议你直接运行的脚本

下面这些是底层检查器,给总入口调用。除非你在排查具体问题,平时不用直接运行:

- `check_skill_contracts.py`
- `check_personas_json.py`
- `check_report_html.py`
- `run_quality_checks.py`
- `test_quality_checks.py`

