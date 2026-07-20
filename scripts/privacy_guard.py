#!/usr/bin/env python3
"""受访者真名泄露守门 — 用户可见过程稿与交付件 ERROR 阻断。

从过程稿收集访谈原始姓名(文件名、分类映射等),扫描 04、05、Markdown
与 report.html 中所有用户可见字段,禁止出现完整真名(约束 8 / P0-PRIVACY)。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.path_utils import iter_artifacts, resolve_process_dir
except ImportError:
    try:
        from path_utils import iter_artifacts, resolve_process_dir
    except ImportError:
        resolve_process_dir = None  # type: ignore
        iter_artifacts = None  # type: ignore

# 展示层允许的脱敏形态(含其一即不视为「裸真名」)
_MASK_MARKERS = ("*", "（", "(", "医生", "同学", "经理", "主管", "工程师", "调度员", "负责人", "运维", "运营", "先生", "女士")
_BARE_NAME_RE = re.compile(r"^[一-鿿]{2,4}$")
_ANONYMOUS_SOURCE_RE = re.compile(r"^P[0-9A-F]{8}$")
_SOURCE_LABEL_RE = re.compile(r"\[来源:([^\]]+)\]")
_SELF_NAME_RE = re.compile(r"(?:我叫|我是|我的名字是|姓名\s*[：:]?)\s*([一-鿿]{2,4})(?=[，,。；;、\s]|$)")
_COMMON_SURNAMES = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉龚程嵇邢裴陆荣翁荀羊甄曲封芮储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通边扈燕冀郏浦尚农温庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公")
_NAME_STOPWORDS = {
    "华为", "用户", "访谈", "逐字稿", "转写稿", "规整稿", "语篇", "专家", "开发者",
    "工程师", "负责人", "管理员", "研究员", "测试员", "产品经理", "模型开发", "算法开发",
}
_DIRECT_IDENTIFIER_PATTERNS = (
    ("P0-PRIVACY-PHONE", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "手机号"),
    ("P0-PRIVACY-LANDLINE", re.compile(r"(?<!\d)0\d{2,3}-?\d{7,8}(?!\d)"), "固定电话"),
    ("P0-PRIVACY-EMAIL", re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[a-z0-9.-]+\.[a-z]{2,}(?![\w.-])"), "邮箱"),
    ("P0-PRIVACY-ID", re.compile(r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)"), "身份证号"),
    ("P0-PRIVACY-ADDRESS", re.compile(r"[一-鿿]{2,}(?:省|市|区|县)[一-鿿]{0,12}(?:路|街|巷|道|小区)\d{1,5}号(?:\d{1,4}(?:栋|单元|室))?"), "精确地址"),
)

# 扫描 JSON 时跳过「仅内部」的键; quote 内若出现他人真名仍报错
_INTERNAL_JSON_KEYS = frozenset({
    "internal_source",
    "raw_name",
    "real_name",
    "source_file",
    "file_stem",
})

_BARE_NAME_CHECK_KEYS = frozenset({
    "display_name",
    "source",
    "representative",
    "representatives",
    "respondent_names",
})

# 必须脱敏的展示字段键名(值会做禁词表检测;裸两字名仅查人物字段)
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


def _looks_like_person_name(value: str) -> bool:
    token = str(value or "").strip()
    return bool(
        _BARE_NAME_RE.fullmatch(token)
        and token[0] in _COMMON_SURNAMES
        and token not in _NAME_STOPWORDS
        and not any(word in token for word in ("访谈", "用户", "专家", "开发", "测试", "模型"))
    )


def _filename_name_candidates(stem: str) -> set[str]:
    """Extract conservative Chinese-name candidates from research filenames."""
    result: set[str] = set()
    raw = str(stem or "").strip()
    if not raw:
        return result
    if _looks_like_person_name(raw):
        result.add(raw)
    for part in re.split(r"[\s_\-—–·.（）()\[\]【】]+", raw):
        token = re.sub(r"^(?:[NPU]\s*)?\d+[号]?[：:]?", "", part, flags=re.I)
        token = re.sub(r"(?:语篇规整稿|规整稿|逐字稿|转写稿|访谈稿|访谈|录音|纪要)$", "", token)
        if _looks_like_person_name(token):
            result.add(token)
    return result


def collect_forbidden_real_names(process_dir: Path) -> set[str]:
    """从过程稿推断禁止出现在展示层的完整姓名/文件名主干。"""
    names: set[str] = set()
    if not process_dir.exists():
        return names

    processed = process_dir / "processed"
    if processed.is_dir():
        files = iter_artifacts(processed, ".txt") if iter_artifacts else processed.rglob("*.txt")
        for p in files:
            stem = p.stem.strip()
            if len(stem) >= 2:
                names.add(stem)
                names.update(_filename_name_candidates(stem))
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                content = ""
            for match in _SELF_NAME_RE.finditer(content[:12000]):
                candidate = match.group(1).strip()
                if _looks_like_person_name(candidate):
                    names.add(candidate)

    extracted = process_dir / "extracted"
    if extracted.is_dir():
        files = iter_artifacts(extracted, ".json") if iter_artifacts else extracted.rglob("*.json")
        for p in files:
            stem = p.stem.strip()
            if len(stem) >= 2:
                names.add(stem)
                names.update(_filename_name_candidates(stem))

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

    manifest_path = process_dir / "source-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}
        for source in manifest.get("sources") or []:
            if not isinstance(source, dict):
                continue
            for filename in source.get("processed_files") or []:
                names.update(_filename_name_candidates(Path(str(filename)).stem))

    return {n for n in names if len(n) >= 2}


def _collect_names_from_obj(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in {"respondent_name", "real_name", "full_name", "file", "source_file", "filename"}:
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


def _direct_identifier_issues(text: str, path: str) -> list[dict]:
    issues: list[dict] = []
    for code, pattern, label in _DIRECT_IDENTIFIER_PATTERNS:
        if pattern.search(text):
            issues.append(_issue("ERROR", code, path, f"用户可见文本含未脱敏{label}"))
    return issues


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

        issues.extend(_direct_identifier_issues(text, path))

        if ".mentioned_by[" in path and not _ANONYMOUS_SOURCE_RE.fullmatch(text.strip()):
            issues.append(_issue(
                "ERROR",
                "P0-PRIVACY-EVIDENCE-SOURCE",
                path,
                "证据来源必须使用 P 加 8 位十六进制字符的匿名 source ID，禁止写姓名或原文件名",
            ))

        for source_label in _SOURCE_LABEL_RE.findall(text):
            if not _ANONYMOUS_SOURCE_RE.fullmatch(source_label.strip()):
                issues.append(_issue(
                    "ERROR",
                    "P0-PRIVACY-EVIDENCE-SOURCE",
                    path,
                    f"证据标签含非匿名来源「{source_label}」；请替换为 source-manifest 中的 P 编号",
                ))

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

        if key in _BARE_NAME_CHECK_KEYS and _BARE_NAME_RE.fullmatch(text.strip()):
            if not _is_masked_display_name(text):
                issues.append(_issue(
                    "ERROR",
                    "P0-PRIVACY-BARE-NAME",
                    path,
                    f"疑似裸真名:「{text}」",
                ))

    return issues


def validate_privacy_in_markdown(
    markdown: str,
    process_dir: Path | None = None,
    *,
    path: str = "04-personas.md",
) -> list[dict]:
    """Scan human-facing checkpoint Markdown before it is delivered."""
    issues = _direct_identifier_issues(markdown, path)
    for source_label in _SOURCE_LABEL_RE.findall(markdown):
        if not _ANONYMOUS_SOURCE_RE.fullmatch(source_label.strip()):
            issues.append(_issue(
                "ERROR",
                "P0-PRIVACY-EVIDENCE-SOURCE-MD",
                path,
                f"用户确认稿的证据来源含姓名或文件名「{source_label}」",
            ))
    if process_dir is not None:
        root = resolve_process_dir(process_dir) if resolve_process_dir else process_dir
        visible = re.sub(r"<!--.*?-->", "", markdown, flags=re.S)
        for name in sorted(collect_forbidden_real_names(root), key=len, reverse=True):
            if name and name in visible:
                issues.append(_issue(
                    "ERROR",
                    "P0-PRIVACY-REAL-NAME-MD",
                    path,
                    f"用户确认稿含访谈真名「{name}」",
                ))
                break
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

    visible_text = re.sub(r"<[^>]+>", " ", html)
    issues.extend(_direct_identifier_issues(visible_text, "html"))
    visible = re.sub(r"\s+", "", visible_text)

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
        if token in forbidden:
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
    parser.add_argument(
        "--write-cache",
        action="store_true",
        help="仅根据 workdir 写入 .privacy_forbidden_names.json",
    )
    args = parser.parse_args()

    process_dir = Path(args.workdir).resolve() if args.workdir else None
    all_issues: list[dict] = []

    if args.write_cache and process_dir is not None:
        root = resolve_process_dir(process_dir) if resolve_process_dir else process_dir
        cache = write_forbidden_names_cache(root)
        print(json.dumps({"success": True, "cache": str(cache)}, ensure_ascii=False, indent=2))
        return 0

    if args.report:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        all_issues.extend(validate_privacy_in_report(report, process_dir))

    if args.html:
        html = Path(args.html).read_text(encoding="utf-8")
        all_issues.extend(validate_privacy_in_html(html, process_dir))

    if process_dir is not None and not args.report and not args.html:
        root = resolve_process_dir(process_dir) if resolve_process_dir else process_dir
        write_forbidden_names_cache(root)
        scanned = []
        for name in ("04-personas.json", "04-journeys.json", "05-report.json"):
            candidate = root / name
            if not candidate.is_file():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                all_issues.append(_issue("ERROR", "P0-PRIVACY-JSON-INVALID", name, str(exc)))
                continue
            all_issues.extend(validate_privacy_in_report(payload, root))
            scanned.append(name)
        if not scanned:
            all_issues.append(_issue(
                "ERROR",
                "P0-PRIVACY-NO-CHECKPOINT",
                str(root),
                "未找到 04-personas.json、04-journeys.json 或 05-report.json，无法执行隐私检查。",
            ))

    errors = [i for i in all_issues if i["level"] == "ERROR"]
    print(json.dumps({"success": not errors, "issues": all_issues}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
