from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.validate_field_alignment import validate_field_alignment


ROOT = Path(__file__).resolve().parents[2]
UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def _data(visual_assets: dict, *, journey: bool = True) -> dict:
    return {
        "version": "1.0",
        "persona_type": "toC",
        "alignment_mode": "custom",
        "field_pool_presented": True,
        "fields_display_names": {"role": "角色"},
        "fields_per_persona": {"persona-1": ["role"]},
        "add_on_pages": {
            "journey": journey,
            "journey_scope": "L2_only" if journey else "none",
        },
        "user_confirmed": True,
        "confirmation_message_summary": "用户确认保留角色字段并生成旅程页面",
        "visual_assets": visual_assets,
        "visual_spec": {
            "template_id": "2c-persona",
            "palette_id": "2c-purple-default",
            "palette_reason": "面向消费者画像并保持同一画像跨页面配色一致",
        },
    }


def test_screenshot_choices_must_be_explicit() -> None:
    errors = validate_field_alignment(_data({"assets_asked": True, "avatar_use_default": True}))
    assert any("scenario_screenshots_enabled" in item for item in errors)

    errors = validate_field_alignment(_data({
        "assets_asked": True,
        "avatar_use_default": True,
        "scenario_screenshots_enabled": True,
    }))
    assert any("screenshots_enabled" in item for item in errors)


def test_screenshot_disabled_cannot_also_be_deferred() -> None:
    errors = validate_field_alignment(_data({
        "assets_asked": True,
        "avatar_use_default": True,
        "scenario_screenshots_enabled": False,
        "scenario_screenshots_deferred": True,
        "screenshots_enabled": False,
    }))
    assert any("不能同时" in item for item in errors)


def test_03_seal_rejects_unchecked_human_decisions(tmp_path: Path) -> None:
    process = tmp_path / "过程稿"
    process.mkdir()
    (process / "03-field-alignment.md").write_text(
        "# 字段与素材确认\n\n- [ ] 是否使用场景截图\n",
        encoding="utf-8",
    )
    (process / "03-field-alignment.json").write_text(
        json.dumps({"status": "draft"}, ensure_ascii=False),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "seal_content_checkpoint.py"),
            "--workdir",
            str(tmp_path),
            "--stem",
            "03-field-alignment",
            "--user-message",
            "确认字段与视觉范围",
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=UTF8_ENV,
    )
    assert proc.returncode != 0
    assert "unchecked decisions" in (proc.stderr + proc.stdout)
