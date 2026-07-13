#!/usr/bin/env python3
"""画像头像解析：用户目录优先，否则回退 skill 内置默认库。"""
from __future__ import annotations

import os
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AVATARS_DIR = SKILL_ROOT / "assets" / "default-avatars"
DELIVERY_AVATAR_DIR = Path("assets") / "画像头像素材"
USER_AVATAR_DIRNAME = "画像头像素材"

_AVATAR_REF_RE = re.compile(r'assets/画像头像素材/([^"\'>\s]+\.png)')
TOC_DEFAULT_POOL = ("内行场景派.png", "认价检索派.png", "优惠深听派.png", "感知场景派.png", "实惠助眠派.png")


def project_dir() -> Path:
    return Path(os.environ.get("PROJECT_DIR", ".")).resolve()


def user_avatar_dir() -> Path:
    return project_dir() / USER_AVATAR_DIRNAME


def resolve_avatar_file(filename: str | None) -> Path | None:
    if not filename:
        return None
    name = Path(filename).name
    user_path = user_avatar_dir() / name
    if user_path.is_file():
        return user_path
    default_path = DEFAULT_AVATARS_DIR / name
    if default_path.is_file():
        return default_path
    return None


def effective_avatar_filename(path: str | None, persona_name: str) -> str | None:
    """用户指定路径 → 画像名.png；任一存在则返回文件名。"""
    if path:
        name = Path(path).name
        if resolve_avatar_file(name):
            return name
    by_name = f"{persona_name}.png"
    if resolve_avatar_file(by_name):
        return by_name
    return None


def avatar_available(path: str | None, persona_name: str | None = None) -> bool:
    if resolve_avatar_file(path):
        return True
    if persona_name:
        return resolve_avatar_file(f"{persona_name}.png") is not None
    return False


def list_default_avatars() -> list[str]:
    if not DEFAULT_AVATARS_DIR.is_dir():
        return []
    return sorted(p.name for p in DEFAULT_AVATARS_DIR.glob("*.png"))


def _base_persona_id(value: str) -> str:
    return re.sub(r"-(?:core|detail(?:-\d+)?|journey)$", "", value)


def _alignment_avatar_mapping(process_dir: Path) -> dict[str, str]:
    path = process_dir / "03-field-alignment.json"
    if not path.is_file():
        return {}
    try:
        import json
        visual = json.loads(path.read_text(encoding="utf-8")).get("visual_assets") or {}
        return {str(k): Path(str(v)).name for k, v in (visual.get("avatar_mapping") or {}).items()}
    except (OSError, ValueError, TypeError):
        return {}


def _persona_names(report: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for page in report.get("personas") or []:
        pid = _base_persona_id(str(page.get("id") or ""))
        name = str(page.get("name") or "").strip()
        if re.fullmatch(r"persona-[0-9]+", pid) and name and pid not in result:
            result[pid] = name
    return result


def preview_default_avatar_assignments(report: dict, process_dir: Path) -> dict[str, str]:
    """Resolve exact/mapped names, then stably assign unused generic defaults."""
    names = _persona_names(report)
    explicit = _alignment_avatar_mapping(process_dir)
    theme = str((report.get("metadata") or {}).get("theme") or "")
    all_defaults = list_default_avatars()
    pool = [name for name in (TOC_DEFAULT_POOL if theme == "2c" else tuple(all_defaults)) if name in all_defaults]
    used: set[str] = set()
    result: dict[str, str] = {}
    for _pid, persona_name in names.items():
        candidates = [explicit.get(persona_name), explicit.get(_pid), f"{persona_name}.png"]
        chosen = next((name for name in candidates if name and resolve_avatar_file(name)), None)
        if not chosen:
            remaining = [name for name in pool if name not in used]
            if remaining:
                chosen = max(
                    remaining,
                    key=lambda filename: SequenceMatcher(None, persona_name, Path(filename).stem).ratio(),
                )
        if chosen:
            used.add(chosen)
            result[persona_name] = chosen
    return result


def apply_default_avatar_assignments(report: dict, process_dir: Path) -> dict[str, str]:
    assignments = preview_default_avatar_assignments(report, process_dir)
    if not assignments:
        return {}
    names = _persona_names(report)
    by_id = {pid: assignments.get(name) for pid, name in names.items()}
    for page in report.get("personas") or []:
        filename = by_id.get(_base_persona_id(str(page.get("id") or "")))
        if not filename:
            continue
        for component in page.get("components") or []:
            props = component.get("props") or {}
            ctype = component.get("type")
            if ctype in {"identity_card", "journey_2c", "detail_illust_corner"} and not props.get("illust_path"):
                props["illust_path"] = f"assets/画像头像素材/{filename}"
            elif ctype == "identity_panel":
                avatar = props.get("persona_avatar") or {}
                if not avatar.get("image_path"):
                    avatar["image_path"] = f"assets/画像头像素材/{filename}"
                    props["persona_avatar"] = avatar
    report.setdefault("metadata", {})["_internal_avatar_assignments"] = assignments
    return assignments


def collect_avatar_filenames_from_json(input_json: dict) -> set[str]:
    names: set[str] = set()
    for persona in input_json.get("personas", []):
        pname = persona.get("name")
        if pname:
            names.add(f"{pname}.png")
        for comp in persona.get("components", []):
            props = comp.get("props") or {}
            av = props.get("persona_avatar") or {}
            if av.get("image_path"):
                names.add(Path(av["image_path"]).name)
            if props.get("illust_path"):
                names.add(Path(props["illust_path"]).name)
    return names


def collect_avatar_filenames_from_html(html: str) -> set[str]:
    return set(_AVATAR_REF_RE.findall(html))


def stage_avatars_to_delivery(output_dir: Path, filenames: set[str]) -> list[str]:
    dest_dir = Path(output_dir) / DELIVERY_AVATAR_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for fn in sorted(filenames):
        src = resolve_avatar_file(fn)
        if not src:
            continue
        dest = dest_dir / fn
        if dest.resolve() != src.resolve():
            shutil.copy2(src, dest)
        copied.append(fn)
    return copied


def infer_project_dir(output_dir: Path) -> Path | None:
    cur = Path(output_dir).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "过程稿").is_dir() and (candidate / USER_AVATAR_DIRNAME).is_dir():
            return candidate
        if (candidate / "过程稿").is_dir():
            return candidate
    return None
