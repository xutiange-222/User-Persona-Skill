from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_TARGETS = [
    ROOT / "renderers",
    ROOT / "layouts",
    ROOT / "schemas",
    ROOT / "REGISTRY.md",
    ROOT.parents[1] / "assets" / "templates" / "_components.css",
]
BAD_PATTERNS = ("???", "AI ????", "assets/????")


def test_component_sources_do_not_contain_known_mojibake_sentinels():
    offenders = []
    for target in TEXT_TARGETS:
        paths = [target] if target.is_file() else list(target.rglob("*"))
        for path in paths:
            if path.suffix not in {".py", ".json", ".md", ".css"}:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in BAD_PATTERNS:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT.parents[1])}: {pattern}")
    assert offenders == []

