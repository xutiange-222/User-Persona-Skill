from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_terminology import validate_terminology


def test_malformed_glossary_returns_diagnostic_instead_of_crashing(tmp_path: Path) -> None:
    (tmp_path / "terminology-glossary.json").write_text(json.dumps({"terms": ["bad"]}), encoding="utf-8")
    errors = validate_terminology(tmp_path)
    assert errors[0]["code"] == "TERMINOLOGY_GLOSSARY_INVALID"


def test_glossary_requires_terms_array(tmp_path: Path) -> None:
    (tmp_path / "terminology-glossary.json").write_text(json.dumps({"terms": {}}), encoding="utf-8")
    errors = validate_terminology(tmp_path)
    assert errors[0]["code"] == "TERMINOLOGY_GLOSSARY_INVALID"
