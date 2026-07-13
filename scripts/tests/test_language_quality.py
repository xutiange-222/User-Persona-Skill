from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.validate_language_quality import validate_language_quality


def _write(path: Path, name: str, data: object) -> None:
    (path / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_language_quality_blocks_truncated_and_invented_technical_terms():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        processed = process / "processed"
        processed.mkdir()
        (processed / "a.txt").write_text("使用 Profiling 和 msprof 完成性能分析。", encoding="utf-8")
        _write(process, "04-personas.json", {"personas": [{"fields": {"task": "Profil 分析", "tool": "Merlin"}}]})
        errors = validate_language_quality(process)
        assert any(item["code"] == "LANGUAGE_TECH_TOKEN_TRUNCATED" for item in errors)
        assert any(item["code"] == "LANGUAGE_TECH_TOKEN_UNGROUNDED" for item in errors)


def test_language_quality_accepts_source_and_user_confirmed_terms():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        processed = process / "processed"
        processed.mkdir()
        (processed / "a.txt").write_text("使用 Profiling 完成分析。", encoding="utf-8")
        _write(process, "03-field-alignment.json", {"custom_fields": ["MindStudio 使用体验"]})
        _write(process, "04-personas.json", {"personas": [{"fields": {"task": "Profiling 分析", "tool": "MindStudio"}}]})
        assert validate_language_quality(process) == []


def test_language_quality_rejects_ellipsis_truncated_human_title():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        _write(
            process,
            "04-personas.json",
            {
                "personas": [
                    {
                        "display_components": [
                            {
                                "type": "titled_list",
                                "props": {
                                    "items": [
                                        {"title": "获取与贡献…", "detail": "获取与贡献算子代码"}
                                    ]
                                },
                            }
                        ]
                    }
                ]
            },
        )
        errors = validate_language_quality(process)
        assert any(item["code"] == "LANGUAGE_TITLE_TRUNCATED" for item in errors)


def test_language_quality_rejects_valid_utf8_with_mojibake_private_use_characters():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        _write(
            process,
            "04-personas.json",
            {"personas": [{"fields": {"summary": "鏍囩鍐呭"}}]},
        )
        errors = validate_language_quality(process)
        assert any(item["code"] == "LANGUAGE_MOJIBAKE" for item in errors)


def test_language_quality_does_not_treat_allowed_html_tags_as_technical_terms(tmp_path: Path):
    (tmp_path / "04-personas.json").write_text(
        json.dumps({"personas": [{"fields": {"summary": "<strong>重点</strong> 内容"}}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert not any(
        item["code"] == "LANGUAGE_TECH_TOKEN_UNGROUNDED"
        and "strong" in item["message"].lower()
        for item in validate_language_quality(tmp_path)
    )
