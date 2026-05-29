#!/usr/bin/env python3
"""画像头像解析：用户目录优先，否则回退 skill 内置默认库。"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AVATARS_DIR = SKILL_ROOT / "assets" / "default-avatars"
DELIVERY_AVATAR_DIR = Path("assets") / "画像头像素材"
USER_AVATAR_DIRNAME = "画像头像素材"

_AVATAR_REF_RE = re.compile(r'assets/画像头像素材/([^"\'>\s]+\.png)')


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
