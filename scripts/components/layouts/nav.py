"""按 persona id 后缀自动配对 single / pair / trio,渲染 nav HTML。

id 命名约定(visual-system.md §3.2):
- persona-N             — 主画像
- persona-N-core        — 双页第一页(2b-grid 拆双页时自动产生)
- persona-N-detail      — 双页第二页 / 2c 专题详情
- persona-N-detail-K    — 2c 多个专题详情(persona-N 多个 detail 页)
- persona-N-journey     — 单画像旅程
- persona-qN            — R4 矩阵象限子画像
- journey-l1            — L1 全景旅程(独立 single)
- matrix / distribution — 首页 layout 容器(不进 nav)

分组规则:
- matrix / distribution 跳过(不进 nav)
- 同 persona-N 前缀的 id 归一桶,桶内组合决定 mode:
  - 仅 persona-N(或仅 persona-N-core)→ single
  - persona-N + persona-N-journey → pair(persona + journey)
  - persona-N-core + persona-N-detail → pair(persona + detail)
  - persona-N + persona-N-detail → pair(persona + detail)
  - persona-N + persona-N-detail + persona-N-journey → trio
  - persona-N-core + persona-N-detail + persona-N-journey → trio
  - persona-N + persona-N-detail-1 + persona-N-detail-2 → trio(多 detail 时占满 detail 位 + journey 位均显示 detail-K)
- persona-qN / journey-l1 → 独立 single
"""
from __future__ import annotations

import re

from ..renderers._utils import escape


def _data_target_attr(group: dict, key: str) -> str:
    tid = group.get(key)
    return f' data-target="{escape(tid, quote=True)}"' if tid else ""


def render_nav_trio(props: dict) -> str:
    groups = []
    for group in props["groups"]:
        mode = group["mode"]
        active = group.get("active", "")
        if mode == "single":
            cls = "nav-btn single" + (" active" if active == "persona" else "")
            groups.append(
                f'<button class="{cls}"{_data_target_attr(group, "persona_id")}>'
                f'{escape(group["persona"])}</button>'
            )
        elif mode == "pair":
            persona_cls = "nav-btn nav-btn-persona" + (" active" if active == "persona" else "")
            journey_cls = "nav-btn nav-btn-journey" + (" active" if active == "journey" else "")
            groups.append(
                '<div class="nav-pair">'
                f'<button class="{persona_cls}"{_data_target_attr(group, "persona_id")}>'
                f'{escape(group["persona"])}</button>'
                f'<button class="{journey_cls}"{_data_target_attr(group, "journey_id")}>'
                f'› {escape(group.get("journey_label", "旅程"))}</button>'
                '</div>'
            )
        else:
            persona_cls = "nav-btn nav-btn-persona" + (" active" if active == "persona" else "")
            detail_cls = "nav-btn nav-btn-detail" + (" active" if active == "detail" else "")
            journey_cls = "nav-btn nav-btn-journey" + (" active" if active == "journey" else "")
            groups.append(
                '<div class="nav-trio">'
                f'<button class="{persona_cls}"{_data_target_attr(group, "persona_id")}>'
                f'{escape(group["persona"])}</button>'
                f'<button class="{detail_cls}"{_data_target_attr(group, "detail_id")}>'
                f'› {escape(group.get("detail_label", "细节"))}</button>'
                f'<button class="{journey_cls}"{_data_target_attr(group, "journey_id")}>'
                f'› {escape(group.get("journey_label", "旅程"))}</button>'
                '</div>'
            )
    return f'<div class="demo-nav-area">{"".join(groups)}</div>'


# All slide ids are eligible for nav; matrix / distribution are single entries.
_NAV_SKIP_IDS: set[str] = set()


def _parse_id(pid: str) -> tuple[str, str | None]:
    """把 id 拆成 (bucket, role)。

    bucket 用来分组(同一个 persona),role 决定它在桶里担任的角色。
    返回:
      ("persona-1", "persona")        — 主画像
      ("persona-1", "core")           — 双页第一页
      ("persona-1", "detail")         — 单 detail 页
      ("persona-1", "detail-1")       — 多 detail 之一
      ("persona-1", "journey")        — 单画像旅程
      ("persona-q1", "persona")       — R4 象限子画像(自成一桶)
      ("journey-l1", "persona")       — L1 全景(自成一桶)
    """
    m = re.match(r"^(persona-\d+)-(core|detail|journey|detail-\d+)$", pid)
    if m:
        return m.group(1), m.group(2)
    return pid, "persona"


def _label_for_role(role: str) -> str:
    """role → nav 按钮右半的文字。"""
    if role == "journey":
        return "旅程"
    if role == "detail":
        return "细节"
    if role.startswith("detail-"):
        return f"专题 {role.split('-', 1)[1]}"
    if role == "core":
        return "核心"
    return ""


def build_nav(personas: list[dict], active_id: str | None = None) -> str:
    """根据 personas 列表自动产 nav HTML。

    active_id:当前激活的画像 id。缺省时取第一个非 skip 的 persona。
    返回 "":  单画像或全是 skip-id 时(_base.html {{persona_nav}} slot 填空)
    """
    nav_personas = [p for p in personas if p["id"] not in _NAV_SKIP_IDS]
    if len(nav_personas) <= 1:
        return ""

    # 默认激活第一个
    if not active_id:
        active_id = nav_personas[0]["id"]

    # 分桶
    buckets: dict[str, dict] = {}
    bucket_order: list[str] = []
    for p in nav_personas:
        bucket, role = _parse_id(p["id"])
        if bucket not in buckets:
            buckets[bucket] = {"roles": {}, "names": {}, "ids": {}}
            bucket_order.append(bucket)
        buckets[bucket]["roles"][role] = True
        buckets[bucket]["names"][role] = p["name"]
        buckets[bucket]["ids"][role] = p["id"]

    # 每个桶决定 mode
    groups = []
    for bucket in bucket_order:
        info = buckets[bucket]
        roles = info["roles"]
        persona_name = info["names"].get("persona") or info["names"].get("core") or next(iter(info["names"].values()))
        persona_id = info["ids"].get("persona") or info["ids"].get("core")

        # 判 active 在桶内
        active_role = None
        for role, pid in info["ids"].items():
            if pid == active_id:
                active_role = role
                break

        detail_roles = [r for r in roles if r == "detail" or r.startswith("detail-")]
        has_journey = "journey" in roles

        # 解析每个槽对应的真实 slide id(给 data-target 用)
        persona_target_id = info["ids"].get("persona") or info["ids"].get("core")
        journey_target_id = info["ids"].get("journey")
        # detail 槽:多 detail 时取第一个;trio 模式下 detail-K 也归 detail 槽
        detail_target_id = info["ids"].get("detail")
        if detail_target_id is None:
            for r, pid in info["ids"].items():
                if r.startswith("detail-"):
                    detail_target_id = pid
                    break

        if len(detail_roles) >= 1 and has_journey:
            detail_role = detail_roles[0]
            groups.append({
                "mode": "trio",
                "persona": persona_name,
                "persona_id": persona_target_id,
                "detail_id": detail_target_id,
                "journey_id": journey_target_id,
                "detail_label": _label_for_role(detail_role),
                "journey_label": "旅程",
                "active": _trio_active(active_role),
            })
        elif has_journey:
            groups.append({
                "mode": "pair",
                "persona": persona_name,
                "persona_id": persona_target_id,
                "journey_id": journey_target_id,
                "journey_label": "旅程",
                "active": _pair_active_journey(active_role),
            })
        elif detail_roles:
            detail_role = detail_roles[0]
            groups.append({
                "mode": "pair",
                "persona": persona_name,
                "persona_id": persona_target_id,
                "journey_id": detail_target_id,  # pair 模式右半字段名是 journey_id(render_nav_trio 接口),内容是 detail id
                "journey_label": _label_for_role(detail_role),
                "active": _pair_active_detail(active_role, detail_role),
            })
        else:
            groups.append({
                "mode": "single",
                "persona": persona_name,
                "persona_id": persona_target_id,
                "active": "persona" if active_role == "persona" else "",
            })

    return render_nav_trio({"groups": groups})


def _trio_active(active_role: str | None) -> str:
    """trio 桶内的 active 槽:persona / detail / journey / ""(空 = 整桶不点亮)。"""
    if active_role is None:
        return ""
    if active_role in ("persona", "core"):
        return "persona"
    if active_role == "journey":
        return "journey"
    if active_role == "detail" or active_role.startswith("detail"):
        return "detail"
    return ""


def _pair_active_journey(active_role: str | None) -> str:
    """pair(persona + journey)桶内 active。active_id 不在桶里 → 整桶不点亮。"""
    if active_role is None:
        return ""
    if active_role == "journey":
        return "journey"
    if active_role in ("persona", "core"):
        return "persona"
    return ""


def _pair_active_detail(active_role: str | None, detail_role: str) -> str:
    """pair(persona + detail)桶内 active。render_nav_trio 的 pair 模式右半 active 用 'journey' 字符串。"""
    if active_role is None:
        return ""
    if active_role == detail_role:
        return "journey"
    if active_role in ("persona", "core"):
        return "persona"
    return ""
