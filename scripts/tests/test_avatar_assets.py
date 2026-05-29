"""默认头像解析与随包复制。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project_with_user_avatar(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        user_dir = root / "画像头像素材"
        user_dir.mkdir()
        (user_dir / "自定义.png").write_bytes(b"user")
        monkeypatch.setenv("PROJECT_DIR", str(root))
        yield root


def test_resolve_user_over_default(monkeypatch, project_with_user_avatar):
    from scripts.avatar_assets import DEFAULT_AVATARS_DIR, resolve_avatar_file

    name = "保障型运维工程师.png"
    if not (DEFAULT_AVATARS_DIR / name).is_file():
        pytest.skip("default avatar not synced yet")
    (project_with_user_avatar / "画像头像素材" / name).write_bytes(b"override")
    assert resolve_avatar_file(name).read_bytes() == b"override"


def test_resolve_default_when_no_user(monkeypatch):
    from scripts.avatar_assets import DEFAULT_AVATARS_DIR, resolve_avatar_file

    name = "保障型运维工程师.png"
    default = DEFAULT_AVATARS_DIR / name
    if not default.is_file():
        pytest.skip("default avatar not synced yet")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("PROJECT_DIR", tmp)
        assert resolve_avatar_file(name) == default


def test_effective_avatar_by_persona_name(monkeypatch):
    from scripts.avatar_assets import DEFAULT_AVATARS_DIR, effective_avatar_filename

    persona = "保障型运维工程师"
    if not (DEFAULT_AVATARS_DIR / f"{persona}.png").is_file():
        pytest.skip("default avatar not synced yet")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("PROJECT_DIR", tmp)
        assert effective_avatar_filename(None, persona) == f"{persona}.png"
