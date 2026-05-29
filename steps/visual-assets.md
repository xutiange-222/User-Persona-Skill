# 用户视觉素材确认（2B / 2C 统一）

> **硬规则**:skill 全流程中,模型**必须主动询问**用户是否补充**画像头像**和**典型场景界面截图**。不能只建空目录、不能只在交付话术里被动提及「如需使用请放入」。  
> **三处检查点前后一致**:字段对齐后(抽取前) → 渲染前 → 交付后说明。

---

## 1. 两类素材与目录

| 素材 | 目录 | 2B(toB/toD) 用于 | 2C(toC) 用于 |
|------|------|-------------------|--------------|
| **画像头像** | 见 §1.1 优先级 | `identity_panel` 左栏头像;旅程页头部插画 | `identity_card` 头像;旅程页头部;`detail_illust_corner` 角落图(可选) |
| **典型场景 / 界面截图** | `<项目运行目录>/界面截图/` | `scenario_grid` 典型业务场景卡片;`business_systems` 场景配图 | `mockup_list` 专题详情产品截图;场景类 grid(若有) |
| **旅程关注点截图**(仅启用旅程页时) | 同上 `界面截图/` | `tob_focus_cell` 关注点卡片 | 旅程触点格(若有截图槽) |

### 1.1 画像头像解析优先级（渲染层硬规则）

1. **用户自定义** — `<项目运行目录>/画像头像素材/<文件名>.png`（同名覆盖默认库）
2. **skill 内置默认库** — `assets/default-avatars/<画像中文名>.png`（skill 包内路径;当前约 14 张示例半身像,来源见该目录 `README.md`）
3. **占位** — 上述两处都找不到匹配文件时,才用色块 + 首字占位

**命名**:头像统一按 `<画像中文名>.png`,例 `调度员.png`、`保障型运维工程师.png`。  
**推荐尺寸**:240×320 px 以上,3:4 半身像,PNG 透明背景为佳。

**与用户交代时必须说明**:
- 你不单独提供头像时,skill **会自动**按画像名从 `assets/default-avatars/` 匹配;不是空白占位
- 只有画像名在默认库里也没有对应文件时,才会显示占位
- 自定义头像放进 `<项目运行目录>/画像头像素材/` 即可覆盖默认

**场景截图命名**:语义化文件名,例 `工单审批.png`、`hires专区首页.png`  
**旅程关注点(可选)**: `focus-<persona_id>-<stage_idx>.png` 或由用户自定 — **必须先确认映射**

---

## 2. 检查点 A — 字段对齐后、写 `03-field-alignment.json` 之前（必问）

在 `steps/field-alignment.md` Step 5 完成旅程页等问题后,**必须**用下面话术询问（2B / 2C 同一套,按对象类型替换示例）:

```
在进入抽取和生成前,还需要确认报告里的图片素材（头像和典型场景截图都会问到）:

1. **画像头像** — 每个画像都可以放一张半身像/角色插画。
   · **自定义路径**:`<项目运行目录>/画像头像素材/`(建议 `<画像中文名>.png`)
   · **默认库**:若你不单独提供,我会按画像名自动匹配 skill 内置 `assets/default-avatars/` 里的示例头像(约 14 张;见该目录 README)
   · **优先级**:你的文件夹同名文件 > 默认库 > 色块占位(仅当两处都没有匹配文件)
   · 想全部用自己的图:放进 `画像头像素材/` 即可覆盖;想换默认库里的某张,也可以只放需要替换的那几张

2. **典型业务/使用场景截图** — 画像页上的「典型场景」「业务系统」「专题详情」等模块可配图。
   · 路径:`<项目运行目录>/界面截图/`
   · 请放产品界面、业务系统、典型使用场景的截图
   · 放好后我会**先列出文件名**,请你确认每张对应哪个场景/哪个画像,不会自动猜
   · 明确说不要时,我用文字描述+占位图标,不假装有图

3. **旅程页关注点截图**（仅当你前面选择要加旅程页时追问）
   · 仍放在 `界面截图/`,用于旅程各阶段关注点卡片
   · 同样先列文件名再确认对应哪个阶段/关注点
   · 明确说不要时,不渲染截图区域

你现在方便提供哪些?可以先说「头像用自己的 / 用默认库 / 稍后补」,有自定义图的话告诉我文件名或放进 `画像头像素材/`。
```

**记录要求** — 写入 `03-field-alignment.json` 的 `visual_assets`(见 §5)。用户说「用默认库 / 不提供自定义头像」记 `avatar_use_default: true`;说「稍后放自定义」记 `avatar_deferred: true`,渲染前必须复检。

---

## 3. 检查点 B — 渲染前（写 `05-report.json` / 调 `render_report.py` 之前）

1. **扫描目录**:
   - `<项目运行目录>/画像头像素材/` 下有哪些**用户自定义**文件
   - 对照各画像名,在 skill `assets/default-avatars/` 中哪些能匹配
   - `界面截图/` 下有哪些文件
2. **对照 `visual_assets`**:
   - 用户说过要提供自定义头像但目录仍空 → **再次提醒**,给路径和命名规则,问「现在放、用默认库、还是先用占位继续渲染」
   - 目录有新文件但 `screenshot_mapping` / `scenario_screenshot_mapping` 未确认 → **列出文件名**,请用户确认映射后再写 `05-report.json` 里的 `screenshot` / `image_path` / `illust_path`
3. **禁止**:未问过用户就直接全部用占位符交付,且交付话术不提「可补图」

**渲染前标准复检话术**:

```
准备渲染报告了。我再看一下图片素材:

· 画像头像(你的):`画像头像素材/` 里 [有 N 张: … / 暂无]
· 画像头像(默认库):按画像名可在 `assets/default-avatars/` 匹配 [M/N 个画像 / 列出未匹配的画像名]
· 典型场景截图:`界面截图/` 里 [有 N 张: … / 暂无]
[若 journey=true] · 旅程关注点截图:[已映射 M 张 / 未提供]

[若用户曾说要补自定义头像但还没有]
你之前说会补自定义头像,目录里还没看到。要我现在用默认库先出报告、等你放进文件夹再重跑,还是继续等?

[若有新文件未映射]
请确认每张图的用途:
- `xxx.png` → 对应哪个画像的哪个场景/关注点?
```

---

## 4. 检查点 C — 渲染后交付

在告知「报告已生成」时,**必须**附带素材状态摘要:

```
报告已生成。关于图片:
· 头像:[已用你的 调度员.png 等 / 已用 skill 默认库 assets/default-avatars/ 中 … / 部分占位: …]
· 典型场景截图:[已使用 … / 未提供,scenario 模块为文字+占位]
· 旅程截图:[…]（未启用旅程则省略）

补自定义头像:放进 `<项目运行目录>/画像头像素材/`(同名覆盖默认库),告诉我后更新并重跑渲染。
默认库路径(skill 包内):`assets/default-avatars/` — 只有画像名在该目录没有对应 png 时才会占位。
```

`交付件说明.md` 中须有一节 **「用户可补充素材」**,列用户目录路径、默认库路径 `assets/default-avatars/`、以及当前使用/占位情况。

---

## 5. `03-field-alignment.json` 记录格式

```json
"visual_assets": {
  "assets_asked": true,
  "assets_asked_at": "field_alignment_step5",
  "avatar_assets_dir": "画像头像素材/",
  "default_avatar_dir": "assets/default-avatars/",
  "avatar_use_default": true,
  "avatar_expected": ["调度员.png", "运维.png"],
  "avatar_provided": false,
  "avatar_deferred": false,
  "scenario_screenshots_enabled": true,
  "scenario_screenshots_deferred": false,
  "scenario_screenshot_mapping": {
    "工单系统.png": "调度员 / scenario_grid / 工单审批场景"
  },
  "screenshots_enabled": true,
  "screenshot_dir": "界面截图/",
  "screenshot_mapping": {
    "发布流水线.png": "运维 / journey / stage_3 关注点"
  },
  "notes": "用户说明天补头像;场景图已放 1 张待确认"
}
```

| 字段 | 含义 |
|------|------|
| `assets_asked` | 是否已在字段对齐阶段问过（必须为 `true` 才能进抽取） |
| `avatar_assets_dir` | 用户自定义头像目录(项目运行目录下) |
| `default_avatar_dir` | skill 内置默认库路径,固定为 `assets/default-avatars/` |
| `avatar_use_default` | 用户未提供自定义头像时,是否使用默认库(true=是,也是默认行为) |
| `avatar_expected` | 计划使用的头像文件名列表(按画像名) |
| `avatar_provided` | 询问时用户目录里是否已有自定义头像 |
| `avatar_deferred` | 用户说稍后补**自定义**头像(非默认库) |
| `scenario_screenshots_enabled` | 用户是否要典型场景截图(false=明确不要) |
| `scenario_screenshot_mapping` | 场景截图文件名 → 用途说明 |
| `screenshots_enabled` | 旅程关注点截图是否启用(仅 journey=true 时相关) |
| `screenshot_mapping` | 旅程截图文件名 → 阶段/关注点 |

用户明确不要某类素材时,对应 `*_enabled: false`,渲染时不假装有图。

---

## 6. 写入 `05-report.json` 时的 props 约定

| 组件 | 头像/截图字段 | 检查路径 |
|------|--------------|----------|
| `identity_panel` | `persona_avatar.image_path` | 用户 `画像头像素材/` → 默认 `assets/default-avatars/` → 占位 |
| `identity_card` / `journey_2c` | `illust_path` | 同上;未写 `illust_path` 时按 `name` 自动匹配 `{name}.png` |
| `scenario_grid` | `scenes[].screenshot` | `界面截图/<filename>` |
| `mockup_list` | `mockups[].screenshot` | `界面截图/<filename>` — **单屏/张**;帧高等宽比缩放见 `visual-system.md` §3.1 |
| `tob_journey_l2` focus | `screenshot` | `界面截图/<filename>` |
| `detail_illust_corner` | `illust_path` | 同头像优先级 |

Python 渲染层(`scripts/avatar_assets.py`)按 §1.1 优先级解析;`render_report.py` 会把实际用到的头像复制进交付件 `assets/画像头像素材/`。**模型仍须在检查点 B/C 告知用户**用了默认库、自定义图还是占位。

---

## 7. 边界情况

- **用户没有自定义头像** → `avatar_provided: false`,`avatar_use_default: true`;按画像名匹配 `assets/default-avatars/`;未匹配才占位;**不反复追问**,但交付时说明默认库路径与可覆盖方式
- **用户明确不要任何头像图(含默认库)** → `avatar_use_default: false`,全部占位(极少见,须用户明确说)
- **用户说不要场景截图** → `scenario_screenshots_enabled: false`,scenario/mockup 用形态 B(文字+占位图标)
- **2C mockup 多图高度不一** → 正常;交付层 CSS 统一帧高,宽按比例缩放,**不要求**用户裁成相同像素尺寸
- **用户说不要旅程截图** → `screenshots_enabled: false`,旅程关注点不渲染截图槽
- **目录有图但用户未确认映射** → **不得**写入 `05-report.json` 的 `screenshot` 字段
- **多画像(R1/R3/R4/R5)** → 每个画像单独列 `avatar_expected`;场景映射注明画像名

---

## 8. 相关文档

- 字段对齐问法嵌入:`steps/field-alignment.md` Step 5.0
- 渲染前门禁:`steps/render-persona-page.md` §1.1
- 视觉规则与复制路径:`steps/visual-system.md` §5.6
- 工作目录:`SKILL.md` 工作目录约定
