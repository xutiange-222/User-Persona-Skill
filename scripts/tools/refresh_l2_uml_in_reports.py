#!/usr/bin/env python3
"""从现有 report.html 解析 tob_journey_l2 数据并重渲染工作流程 UML 单元格。"""
from __future__ import annotations

import argparse
import html as html_lib
import re
import sys
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V9))

from scripts.components.renderers.tob_journey import (
    _is_decision_question,
    _normalize_focus_token,
    _render_uml_journey,
)

# 旧版 HTML 常把痛点标题画进菱形 — 刷新时改回问句型判断
_PAIN_DECISION_RELABEL: dict[str, str] = {
    "算力耗时": "路径会超载？",
    "多方协同": "需协同发令？",
    "分钟级演算": "可秒级演算？",
    "告警定位粗": "告警可精确定位？",
    "固定尖峰提醒": "需定时提醒？",
    "无量化控量": "控量可量化？",
    "电话问燃机": "燃机可及时并网？",
    "数据错位": "上报数据一致？",
    "省际洽谈": "外送通道可用？",
    "储能补峰": "需储能补峰？",
    "判责分级": "责任可明确？",
    "监控可见": "监控可覆盖？",
    "接口齐了吗": "接口已对齐？",
}

NODE_RE = re.compile(
    r'<g class="l1-node l1-(\w+)" transform="translate\(([\d.]+) ([\d.]+)\)">'
    r'[\s\S]*?<div[^>]*class="l1-node-label(?: small)?">([^<]+)</div>',
    re.MULTILINE,
)
EDGE_RE = re.compile(r'<path class="l1-connector[^"]*" d="([^"]+)"')
BRANCH_RE = re.compile(
    r'<g class="l1-branch-label-pill">[\s\S]*?<text class="l1-branch-label"[^>]*>([^<]+)</text>'
)


def _slug(name: str, idx: int) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or f"stage_{idx}"


def _path_endpoints(d: str) -> tuple[tuple[float, float], tuple[float, float]]:
    m = re.match(r"M\s*([\d.]+)\s+([\d.]+)", d)
    if not m:
        raise ValueError(f"bad path: {d[:40]}")
    sx, sy = float(m.group(1)), float(m.group(2))
    hs = re.findall(r"H\s*([\d.]+)", d)
    vs = re.findall(r"V\s*([\d.]+)", d)
    tx = float(hs[-1]) if hs else sx
    ty = float(vs[-1]) if vs else sy
    return (sx, sy), (tx, ty)


def _nearest_id(
    point: tuple[float, float],
    centers: dict[str, tuple[float, float]],
) -> str:
    px, py = point
    return min(
        centers.keys(),
        key=lambda nid: (centers[nid][0] - px) ** 2 + (centers[nid][1] - py) ** 2,
    )


def _dedupe_edges(edges: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str | None]] = set()
    out: list[dict] = []
    for e in edges:
        key = (e["from"], e["to"], e.get("branch"))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _has_edge(edges: list[dict], edge: dict) -> bool:
    return any(
        x["from"] == edge["from"] and x["to"] == edge["to"] for x in edges
    )


def _normalize_l2_edges(
    nodes: list[dict],
    centers: dict[str, tuple[float, float]],
    raw_edges: list[dict],
    branch_labels: list[str],
) -> list[dict]:
    """L2 单泳道：路径反推易误配（自环/断连），用 x 序主链 + 决策多出口修正。"""
    ordered = sorted(nodes, key=lambda n: (centers[n["id"]][0], n["id"]))
    decision_ids = {n["id"] for n in nodes if n["type"] == "decision"}

    # 主链：决策节点不作为链式 from（出边由 raw + 默认「是」分支补齐）
    edges: list[dict] = []
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i + 1]
        if a["type"] == "decision":
            continue
        edges.append({"from": a["id"], "to": b["id"]})

    for e in raw_edges:
        if e["from"] == e["to"]:
            continue
        if e["from"] in decision_ids:
            if not _has_edge(edges, e):
                edges.append(e)

    # 决策默认「是」：沿 x 序前进到下一节点（若 raw 未提供前向出边）
    for n in ordered:
        if n["type"] != "decision":
            continue
        dec_id = n["id"]
        fx = centers[dec_id][0]
        has_forward = any(
            centers[e["to"]][0] > fx + 20
            for e in edges
            if e["from"] == dec_id
        )
        if has_forward:
            continue
        idx = next(i for i, o in enumerate(ordered) if o["id"] == dec_id)
        if idx + 1 < len(ordered):
            nxt = ordered[idx + 1]
            edges.append({"from": dec_id, "to": nxt["id"]})

    # 非决策节点的回跳边（少见）
    for e in raw_edges:
        if e["from"] == e["to"] or e["from"] in decision_ids:
            continue
        if centers[e["to"]][0] < centers[e["from"]][0] - 40 and not _has_edge(edges, e):
            edges.append(e)

    decisions_ordered = [n for n in ordered if n["type"] == "decision"]
    for dec in decisions_ordered:
        outs = [e for e in edges if e["from"] == dec["id"]]
        dec_idx = next(i for i, o in enumerate(ordered) if o["id"] == dec["id"])
        if len(outs) == 0 and dec_idx + 1 < len(ordered):
            edges.append(
                {"from": dec["id"], "to": ordered[dec_idx + 1]["id"], "branch": "yes"}
            )
        elif len(outs) == 1 and not outs[0].get("branch"):
            outs[0]["branch"] = "yes"
        # 不再自动补装饰性「否」分支 — 无独立补救任务时只保留「是」主线

    return _dedupe_edges(edges)


def _parse_focus_titles(section_html: str) -> set[str]:
    titles = re.findall(
        r'class="tob-focus-card-title"[^>]*>([^<]+)<', section_html
    )
    return {_normalize_focus_token(html_lib.unescape(t).strip()) for t in titles}


def _repair_l2_props(props: dict, section_html: str) -> None:
    """菱形须为流程判断;与 focuses 标题重复的改为问句或 step。"""
    focus_titles = _parse_focus_titles(section_html)
    for node in props["nodes"]:
        if node.get("type") != "decision":
            continue
        label = str(node.get("label", "")).strip()
        norm = _normalize_focus_token(label)
        if norm in focus_titles or label in _PAIN_DECISION_RELABEL:
            node["label"] = _PAIN_DECISION_RELABEL.get(
                label, f"是否{label.rstrip('?？')}？"
            )
        elif not _is_decision_question(label):
            if label.endswith("?") and not label.endswith("？"):
                node["label"] = label[:-1] + "？"
            elif not label.endswith("？"):
                node["label"] = f"{label}？"


def _parse_l2_section(section_html: str) -> dict:
    banner_title_m = re.search(r'<div class="tob-banner-title">([^<]+)</div>', section_html)
    banner_sub_m = re.search(r'<div class="tob-banner-subtitle">([^<]+)</div>', section_html)
    stage_tags = re.findall(
        r'<div class="tob-stage-tag"><span class="tob-stage-number">\d+</span>([^<]+)</div>',
        section_html,
    )
    substage_bars = re.findall(
        r'<div class="tob-substage-cell l1-substage-bar">(.*?)</div>',
        section_html,
        flags=re.DOTALL,
    )
    tools_cells = re.findall(
        r'<div class="tob-tools-cell">(.*?)</div>', section_html, flags=re.DOTALL
    )

    stages = []
    for idx, name in enumerate(stage_tags):
        subs = []
        if idx < len(substage_bars):
            subs = [
                html_lib.unescape(s)
                for s in re.findall(r"<span>([^<]+)</span>", substage_bars[idx])
            ]
        stages.append({"id": _slug(name, idx), "name": name.strip(), "subStages": subs})

    tools_touchpoints = []
    for cell in tools_cells[: len(stages)]:
        tags = [
            html_lib.unescape(t)
            for t in re.findall(r'<span class="tob-tools-tag">([^<]+)</span>', cell)
        ]
        tools_touchpoints.append(tags)

    lane_id = "lane_0"
    lanes = [{"id": lane_id, "name": "主流程", "tag": ""}]

    uml_m = re.search(r'<div class="tob-l2-uml-cell">(.*?)<div class="tob-focus-cell">', section_html, re.DOTALL)
    uml_html = uml_m.group(1) if uml_m else section_html

    parsed = []
    for node_type, x_s, y_s, label in NODE_RE.findall(uml_html):
        parsed.append(
            {
                "type": node_type,
                "x": float(x_s),
                "y": float(y_s),
                "label": html_lib.unescape(label).strip(),
            }
        )
    if not parsed:
        raise ValueError("未从 HTML 解析到 UML 节点")

    svg_w = 1180.0
    rail_w = 0.0
    stage_w = (svg_w - rail_w) / max(1, len(stages))
    stage_ranges = [
        (rail_w + i * stage_w, rail_w + (i + 1) * stage_w) for i in range(len(stages))
    ]

    def stage_index(x: float) -> int:
        for i, (x1, x2) in enumerate(stage_ranges):
            if x1 <= x < x2 or (i == len(stage_ranges) - 1 and x >= x1):
                return i
        return min(len(stage_ranges) - 1, max(0, int((x - rail_w) / stage_w)))

    nodes = []
    centers: dict[str, tuple[float, float]] = {}
    for idx, item in enumerate(parsed):
        st_idx = stage_index(item["x"])
        same = [n for n in parsed if stage_index(n["x"]) == st_idx]
        same.sort(key=lambda n: n["x"])
        slot = same.index(item)
        nid = f"n{idx + 1}"
        nodes.append(
            {
                "id": nid,
                "lane": lane_id,
                "stage": stages[st_idx]["id"],
                "type": item["type"],
                "slot": slot,
                "label": item["label"],
            }
        )
        centers[nid] = (item["x"] + 42, item["y"] + 22)

    branch_labels = BRANCH_RE.findall(uml_html)
    raw_edges = []
    for d in EDGE_RE.findall(uml_html):
        start, end = _path_endpoints(d)
        raw_edges.append(
            {
                "from": _nearest_id(start, centers),
                "to": _nearest_id(end, centers),
            }
        )
    edges = _normalize_l2_edges(nodes, centers, raw_edges, branch_labels)

    return {
        "banner_title": html_lib.unescape(banner_title_m.group(1)).strip() if banner_title_m else "",
        "banner_subtitle": html_lib.unescape(banner_sub_m.group(1)).strip() if banner_sub_m else "",
        "stages": stages,
        "lanes": lanes,
        "tools_touchpoints": tools_touchpoints,
        "nodes": nodes,
        "edges": edges,
    }


def refresh_report(path: Path) -> int:
    html = path.read_text(encoding="utf-8")
    changed = 0
    matches = list(
        re.finditer(
            r'(<section class="persona-slide[^"]*layout-2b-journey is-l2[^"]*" id="([^"]+)"[^>]*>)(.*?)(</section>)',
            html,
            flags=re.DOTALL,
        )
    )
    for m in reversed(matches):
        sec_open, sec_id, body, sec_close = m.groups()
        if "tob-l2-uml-hybrid" not in body:
            continue
        focus_m = re.search(r"(<div class=\"tob-focus-cell\">.*)", body, re.DOTALL)
        if not focus_m:
            continue
        focus_html = focus_m.group(1)
        prefix_m = re.match(r"(.*?<div class=\"tob-l2-uml-cell\">)", body, re.DOTALL)
        if not prefix_m:
            continue
        props = _parse_l2_section(body)
        _repair_l2_props(props, focus_html)
        from scripts.components.renderers.tob_journey import _sanitize_invalid_no_branches

        _sanitize_invalid_no_branches(props["edges"])
        props["marker_id"] = re.sub(r"[^a-zA-Z0-9_]", "_", sec_id)
        new_uml = _render_uml_journey(
            props,
            show_lane_rail=False,
            density_mode="l2",
            validate_density=False,
        )
        new_body = prefix_m.group(1) + new_uml + "</div>" + focus_html
        new_section = sec_open + new_body + sec_close
        html = html[: m.start()] + new_section + html[m.end() :]
        changed += 1
        print(f"  refreshed {sec_id}")

    if changed:
        path.write_text(html, encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="重渲染 report 内 L2 UML 工作流程格")
    parser.add_argument("reports", nargs="*", help="report.html 路径")
    args = parser.parse_args()
    default_paths = [
        V9 / "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html",
        V9 / "docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html",
        V9 / "docs/reference/reports/D-二维矩阵/2B-电力调度员/report.html",
        V9.parent / "user-persona-v8/说明书-样例/2B-DevOps多角色旅程/report.html",
        V9.parent
        / "user-persona-v8/用户画像报告输出/电力调度员-20260529-1654/最终交付件-2B-电力调度员-5用户-2维/report.html",
    ]
    paths = [Path(p) for p in args.reports] if args.reports else default_paths
    total = 0
    for p in paths:
        if not p.is_file():
            print(f"skip missing {p}")
            continue
        try:
            print(p.relative_to(V9))
        except ValueError:
            print(p)
        total += refresh_report(p)
    print(f"done: {total} L2 section(s)")


if __name__ == "__main__":
    main()
