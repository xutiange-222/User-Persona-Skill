import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jsonschema import validate

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None

from components.registry import render_component


SAMPLES_DIR = Path(__file__).parent / "golden_samples"
SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"



class _DomSerializer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attr_text = "".join(f' {name}="{value or ""}"' for name, value in sorted(attrs))
        self.parts.append(f"<{tag}{attr_text}>")

    def handle_startendtag(self, tag, attrs):
        attr_text = "".join(f' {name}="{value or ""}"' for name, value in sorted(attrs))
        self.parts.append(f"<{tag}{attr_text}/>")

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)


def normalize_dom(html: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(string=lambda t: t.strip() == ""):
            el.extract()
        return soup.prettify()
    parser = _DomSerializer()
    parser.feed(html)
    return "\n".join(parser.parts)



@pytest.mark.parametrize("json_file", sorted(SAMPLES_DIR.glob("*.json")))
def test_golden_sample_json_matches_schema(json_file):
    input_json = json.loads(json_file.read_text(encoding="utf-8"))
    schema_file = SCHEMAS_DIR / f"{input_json['type']}.json"
    assert schema_file.exists(), f"?? schema: {schema_file.name}"
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validate(instance=input_json["props"], schema=schema)

@pytest.mark.parametrize(
    "sample_name",
        [
            "tob_journey_l1_uml",
            "tob_journey_l1_dense",
            "tob_journey_l2",
        ],
)
def test_dom_diff(sample_name):
    expected_html = (SAMPLES_DIR / f"{sample_name}.html").read_text(encoding="utf-8")
    input_json = json.loads((SAMPLES_DIR / f"{sample_name}.json").read_text(encoding="utf-8"))
    actual_html = render_component(input_json)
    assert normalize_dom(expected_html) == normalize_dom(actual_html), f"{sample_name} DOM 不一致"
