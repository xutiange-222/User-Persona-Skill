from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from scripts.resolve_content_refs import resolve_report_content_refs, validate_report_content_refs
from scripts.validate_journey_checkpoint import _evidence_binding_errors
from scripts.validate_evidence_contract import validate_evidence_contract
from scripts.validate_source_manifest import validate_source_manifest


def test_source_manifest_uses_unique_primary_count_and_assignments():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp) / "过程稿"
        source = process / "processed" / "group" / "a.txt"
        source.parent.mkdir(parents=True)
        source.write_text("访谈内容", encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest = {
            "version": "1.0", "status": "reviewed",
            "sources": [{
                "source_id": "P" + digest[:8].upper(), "processed_files": ["group/a.txt"],
                "content_sha256": digest, "evidence_tier": "primary",
                "assigned_personas": ["persona-1", "persona-2"],
                "inclusion_reason": "核心研究对象", "supplemented_fields": [],
            }],
            "reference_files": [],
            "counts": {"unique_primary_interviews": 1, "unique_supplemental_sources": 0, "analysis_assignment_count": 2},
        }
        (process / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        assert validate_source_manifest(process) == []


def test_report_persona_content_must_resolve_from_confirmed_04():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        canonical = {"type": "generic_text", "props": {"text": "完整术语 Profiling"}, "source_fields": ["role"]}
        (process / "04-personas.json").write_text(json.dumps({"personas": [{"id": "persona-1", "name": "工程师", "display_components": [canonical]}]}, ensure_ascii=False), encoding="utf-8")
        (process / "03-field-alignment.json").write_text(json.dumps({"fields_per_persona": {"persona-1": ["role"]}}, ensure_ascii=False), encoding="utf-8")
        report = {
            "metadata": {"field_coverage": [{"persona_id": "persona-1", "included_fields": ["role"], "omitted_fields": []}]},
            "personas": [{"id": "persona-1", "layout": "layout-2b-grid", "components": [{"type": "generic_text", "content_ref": "/personas/0/display_components/0"}]}],
        }
        assert validate_report_content_refs(report, process) == []
        assert resolve_report_content_refs(report, process)["personas"][0]["components"][0] == {"type": "generic_text", "props": canonical["props"]}
        report["personas"][0]["components"][0]["props"] = {"text": "Profil"}
        assert any(item["code"] == "PERSONA_CONTENT_REF_WITH_PROPS" for item in validate_report_content_refs(report, process))


def test_report_cannot_silently_drop_confirmed_field():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        canonical = {"type": "generic_text", "props": {"text": "角色"}, "source_fields": ["role"]}
        personas = {"personas": [{"id": "persona-1", "name": "工程师", "display_components": [canonical]}]}
        alignment = {"fields_per_persona": {"persona-1": ["role", "pain_points"]}}
        report = {
            "metadata": {"field_coverage": [{"persona_id": "persona-1", "included_fields": ["role"], "omitted_fields": []}]},
            "personas": [{"id": "persona-1", "layout": "layout-2b-grid", "components": [{"type": "generic_text", "content_ref": "/personas/0/display_components/0"}]}],
        }
        (process / "04-personas.json").write_text(json.dumps(personas, ensure_ascii=False), encoding="utf-8")
        (process / "03-field-alignment.json").write_text(json.dumps(alignment, ensure_ascii=False), encoding="utf-8")
        errors = validate_report_content_refs(report, process)
        assert any(item["code"] == "REPORT_FIELD_COVERAGE_INCOMPLETE" for item in errors)


def test_supplemental_only_journey_node_is_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        manifest = {"sources": [{"source_id": "P12345678", "evidence_tier": "supplemental"}]}
        (process / "source-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        data = {"journeys": [{
            "component_type": "tob_journey_l2",
            "props": {"stages": [{"id": "s1"}], "nodes": [{"id": "n1"}], "edges": []},
            "evidence_bindings": [
                {"target": "stage:s1", "evidence_type": "synthesis", "source_ids": [], "quote_or_basis": "综合节点"},
                {"target": "node:n1", "evidence_type": "supplemental", "source_ids": ["P12345678"], "quote_or_basis": "旁证"},
            ],
        }]}
        errors = _evidence_binding_errors(data, process)
        assert any(item["code"] == "JOURNEY_SUPPLEMENTAL_ONLY" for item in errors)


def test_mechanical_evidence_bundle_reuse_is_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        quote = '[来源:P12345678]: "同一句原话"'
        node = {"mention_count": 1, "mentioned_by": ["P12345678"], "evidence_quotes": [quote]}
        personas = {"personas": [{"id": "persona-1", "members": ["P12345678"], "fields": {"role": node, "team": node, "tool": node}}]}
        manifest = {"sources": [{"source_id": "P12345678", "assigned_personas": ["persona-1"]}]}
        (process / "04-personas.json").write_text(json.dumps(personas, ensure_ascii=False), encoding="utf-8")
        (process / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        errors = validate_evidence_contract(process)
        assert any(item["code"] == "EVIDENCE_BUNDLE_REUSED" for item in errors)
