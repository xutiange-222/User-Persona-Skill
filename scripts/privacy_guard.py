#!/usr/bin/env python3
"""受访者真名泄露守门 — 交付前 ERROR 阻断。

从过程稿收集访谈原始姓名(文件名、分类映射等),扫描 05-report.json 与 report.html
中所有用户可见字段,禁止出现完整真名(约束 8 / P0-PRIVACY)。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

try:
    from path_utils import resolve_process_dir
except ImportError:
    resolve_process_dir = None  # type: ignore

# 展示层允许的脱敏形态(含其一即不视为「裸真名」)
_MASK_MARKERS = ("*", "（", "(", "医生", "同学", "经理", "主管", "工程师", "调度员", "负责人", "运维", "运营", "先生", "女士")
_BARE_NAME_RE = re.compile(r"^[一-鿿]{2,4}$")

# 扫描 JSON 时跳过「仅内部」的键; quote 内若出现他人真名仍报错
_INTERNAL_JSON_KEYS = frozenset({
    "internal_source",
    "raw_name",
    "real_name",
    "source_file",
    "file_stem",
})

# 必须脱敏的展示字段键名(值会做裸名/禁词表检测)
_DISPLAY_JSON_KEYS = frozenset({
    "display_name",
    "source",
    "summary",
    "body",
    "title",
    "detail",
    "identity_desc",
    "name-line",
    "osn-source",
    "quote-source",
    "meta-value",
    "meta_value",
    "value",
    "label",
    "caption",
    "mention_badge",
    "representative",
    "representatives",
    "respondent_names",
    "fingerprints",
})


def _walk_strings(obj: Any, path: str = "$") -> Iterable[tuple[str, str, str]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path != "$" else f"$.{k}"
            if k in _INTERNAL_JSON_KEYS:
                continue
            yield from _walk_strings(v, child)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, path.rsplit(".", 1)[-1], obj


def _is_masked_display_name(name: str) -> bool:
    s = (name or "").strip()
    if not s:
        return False
    if re.fullmatch(r"受访者\d+", s):
        return False
    if re.fullmatch(r"U\d+(_[一-鿿]+)?", s):
        return True
    if any(m in s for m in _MASK_MARKERS):
        return True
    if _BARE_NAME_RE.fullmatch(s):
        return False
    return True


def collect_forbidden_real_names(process_dir: Path) -> set[str]:
    """从过程稿推断禁止出现在展示层的完整姓名/文件名主干。"""
    names: set[str] = set()
    if not process_dir.exists():
        return names

    processed = process_dir / "processed"
    if processed.is_dir():
        for p in processed.glob("*.txt"):
            stem = p.stem.strip()
            if len(stem) >= 2:
                names.add(stem)

    extracted = process_dir / "extracted"
    if extracted.is_dir():
        for p in extracted.glob("*.json"):
            stem = p.stem.strip()
            if len(stem) >= 2:
                names.add(stem)

    cache = process_dir / ".privacy_forbidden_names.json"
    if cache.is_file():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            for n in data.get("forbidden", []):
                if isinstance(n, str) and n.strip():
                    names.add(n.strip())
        except (json.JSONDecodeError, OSError):
            pass

    for fname in ("02-classification.json", "04-personas.json"):
        p = process_dir / fname
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        _collect_names_from_obj(data, names)

    return {n for n in names if len(n) >= 2}


def _collect_names_from_obj(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in {"name", "respondent_name", "real_name", "full_name", "file", "source_file", "filename"}:
                if isinstance(v, str) and 2 <= len(v.strip()) <= 8:
                    out.add(v.strip())
                    stem = Path(v.strip()).stem
                    if len(stem) >= 2:
                        out.add(stem)
            _collect_names_from_obj(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_names_from_obj(item, out)


def write_forbidden_names_cache(process_dir: Path, extra: Iterable[str] | None = None) -> Path:
    """写入/更新禁名表,供后续校验与续跑。"""
    names = collect_forbidden_real_names(process_dir)
    if extra:
        names.update(x.strip() for x in extra if x and str(x).strip())
    cache = process_dir / ".privacy_forbidden_names.json"
    cache.write_text(
        json.dumps({"forbidden": sorted(names)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cache


def _issue(level: str, code: str, path: str, message: str) -> dict:
    return {"level": level, "code": code, "path": path, "message": message}


def validate_privacy_in_report(
    report: dict,
    process_dir: Path | None = None,
) -> list[dict]:
    """扫描 components JSON,返回 P0-PRIVACY 问题列表。"""
    issues: list[dict] = []
    forbidden: set[str] = set()
    if process_dir is not None:
        root = resolve_process_dir(process_dir) if resolve_process_dir else process_dir
        forbidden = collect_forbidden_real_names(root)

    for path, key, text in _walk_strings(report):
        if not text or not text.strip():
            continue

        if key in ("display_name", "source") or path.endswith(".display_name") or path.endswith(".source"):
            if not _is_masked_display_name(text):
                issues.append(_issue(
                    "ERROR",
                    "P0-PRIVACY-DISPLAY-NAME",
                    path,
                    f"展示名未脱敏:「{text}」须改为 姓氏+* / 身份(如张医生) / U1,禁止裸真名",
                ))

        for name in sorted(forbidden, key=len, reverse=True):
            if name in text:
                issues.append(_issue(
                    "ERROR",
                    "P0-PRIVACY-REAL-NAME",
                    path,
                    f"用户可见文本含访谈真名「{name}」:须改为脱敏指代;聚合画像禁止在正文/代表人群中逐人点名",
                ))
                break

        if key in _DISPLAY_JSON_KEYS and _BARE_NAME_RE.fullmatch(text.strip()):
            if not _is_masked_display_name(text):
                issues.append(_issue(
                    "ERROR",
                    "P0-PRIVACY-BARE-NAME",
                    path,
                    f"疑似裸真名:「{text}」",
                ))

    return issues


def validate_privacy_in_html(
    html: str,
    process_dir: Path | None = None,
) -> list[dict]:
    """扫描渲染后 HTML 可见文本(去标签)。"""
    issues: list[dict] = []
    forbidden: set[str] = set()
    if process_dir is not None:
        root = resolve_process_dir(process_dir) if resolve_process_dir else process_dir
        forbidden = collect_forbidden_real_names(root)

    visible = re.sub(r"<[^>]+>", "", html)
    visible = re.sub(r"\s+", "", visible)

    for pat in (re.compile(r">受访者\d+<"), re.compile(r">U\d+_[一-鿿]+<")):
        if pat.search(html):
            issues.append(_issue(
                "ERROR",
                "P0-PRIVACY-CODE",
                "html",
                f"展示层出现内部代号:{pat.pattern}",
            ))

    for name in forbidden:
        if name and name in visible:
            issues.append(_issue(
                "ERROR",
                "P0-PRIVACY-REAL-NAME-HTML",
                "html",
                f"HTML 可见文本含访谈真名「{name}」",
            ))

    for m in re.finditer(r">([一-鿿]{2,3})<", html):
        token = m.group(1)
        if _is_masked_display_name(token):
            continue
        if token in forbidden or _BARE_NAME_RE.fullmatch(token):
            issues.append(_issue(
                "ERROR",
                "P0-PRIVACY-BARE-NAME-HTML",
                "html",
                f"HTML 标签内疑似裸真名:「{token}」",
            ))

    return issues


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="受访者真名泄露检查")
    parser.add_argument("--report", help="05-report.json 路径")
    parser.add_argument("--html", help="report.html 路径")
    parser.add_argument("--workdir", help="过程稿或项目运行目录")
    args = parser.parse_args()

    process_dir = Path(args.workdir).resolve() if args.workdir else None
    all_issues: list[dict] = []

    if args.report:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        all_issues.extend(validate_privacy_in_report(report, process_dir))

    if args.html:
        html = Path(args.html).read_text(encoding="utf-8")
        all_issues.extend(validate_privacy_in_html(html, process_dir))

    errors = [i for i in all_issues if i["level"] == "ERROR"]
    print(json.dumps({"success": not errors, "issues": all_issues}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
