#!/usr/bin/env python3
"""Regression tests for the machine-readable design system and 2C palette gates."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPT_DIR.parent
for path in (SCRIPT_DIR, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.components.layouts.layout_rules import accent_inline  # noqa: E402
from scripts.components.validate import _check_toc_palette_mapping  # noqa: E402
from scripts.components.visual_system import load_visual_system  # noqa: E402
from validate_html import (  # noqa: E402
    Report,
    _check_2c_font_floor,
    _check_2c_palette_packs,
    _check_workflow_visual_spec,
)


class VisualSystemTests(unittest.TestCase):
    def test_visual_system_has_four_layers_and_six_toc_palettes(self):
        system = load_visual_system()
        self.assertEqual(
            system["layers"],
            ["foundations", "semantic_tokens", "themes", "component_contracts"],
        )
        palettes = system["themes"]["2c"]["palette_packs"]
        self.assertEqual(len(palettes), 6)
        required = {
            "--color-accent",
            "--color-toc-style",
            "--color-toc-primary",
            "--color-toc-secondary",
            "--color-toc-surface",
            "--color-toc-bg",
            "--color-toc-soft",
            "--color-toc-alert",
            "--color-toc-aux",
            "--color-toc-aux-bg",
            "--color-toc-aux-text",
        }
        for pack in palettes.values():
            self.assertEqual(set(pack["values"]), required)

    def test_renderer_uses_visual_system_and_rejects_deprecated_accent(self):
        self.assertIn("--color-toc-style: yellow-orange", accent_inline("mustard"))
        with self.assertRaises(ValueError):
            accent_inline("clay-red")

    def test_palette_validator_blocks_primary_colored_aux_tag(self):
        style = accent_inline("purple")[len('style="'):-1]
        style = style.replace(
            "--color-toc-aux-bg: var(--palette-2c-purple-aux)",
            "--color-toc-aux-bg: var(--palette-2c-purple-primary)",
        )
        html = (
            '<section class="persona-slide layout-2c-journey" '
            f'id="persona-1-journey" style="{style}"></section>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            rep = Report(Path(tmp) / "report.html")
            _check_2c_palette_packs(html, rep)
            codes = {issue.code for issue in rep.errors}
            self.assertIn("VSTYLE-2C-PALETTE-VALUE-MISMATCH", codes)
            self.assertIn("VSTYLE-2C-TOUCHPOINT-PRIMARY-COLOR", codes)

    def test_font_floor_blocks_10px_distribution_text(self):
        css = ".distribution-footer-hint { font-size: 10px; }"
        html = '<section class="persona-slide layout-distribution-multi"></section>'
        with tempfile.TemporaryDirectory() as tmp:
            rep = Report(Path(tmp) / "report.html")
            _check_2c_font_floor(css, html, rep)
            self.assertTrue(any(issue.code == "VSTYLE-2C-FONT-BELOW-MIN" for issue in rep.errors))

    def test_same_persona_cannot_mix_palettes_across_pages(self):
        portrait = accent_inline("purple")[len('style="'):-1]
        journey = accent_inline("moss-green")[len('style="'):-1]
        html = (
            '<section class="persona-slide layout-2c-portrait" '
            f'id="persona-1" style="{portrait}"></section>'
            '<section class="persona-slide layout-2c-journey" '
            f'id="persona-1-journey" style="{journey}"></section>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            rep = Report(Path(tmp) / "report.html")
            _check_2c_palette_packs(html, rep)
            self.assertTrue(
                any(issue.code == "VSTYLE-2C-PALETTE-STYLE-MISMATCH" for issue in rep.errors)
            )

    def test_workflow_html_requires_visual_spec_in_03_and_05(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            process = project / "过程稿"
            process.mkdir()
            (process / "03-field-alignment.json").write_text("{}", encoding="utf-8")
            (process / "05-report.json").write_text('{"metadata": {}}', encoding="utf-8")
            rep = Report(project / "交付件" / "report.html")
            _check_workflow_visual_spec(rep, project)
            self.assertTrue(
                any(issue.code == "VSTYLE-VISUAL-SPEC-MISSING" for issue in rep.errors)
            )

    def test_components_json_requires_palette_map_for_complex_2c(self):
        report = {
            "metadata": {
                "theme": "2c",
                "density": "low",
                "persona_count": 2,
                "visual_spec": {"template_id": "2c-complex-distribution-report"},
            },
            "personas": [
                {"id": "persona-1", "layout": "layout-2c-portrait", "accent": "purple"},
                {"id": "persona-2", "layout": "layout-2c-portrait", "accent": "moss-green"},
            ],
        }
        issues = _check_toc_palette_mapping(report)
        self.assertTrue(any(item["code"] == "P8-2C-PALETTE-MAP-MISSING" for item in issues))

    def test_journey_header_contract_uses_surface_layer(self):
        contract = load_visual_system()["component_contracts"]["2c_journey_stage_header"]
        self.assertIn("--color-toc-surface", contract["background"])
        self.assertEqual(contract["color"], "var(--color-text-primary)")


if __name__ == "__main__":
    unittest.main()
