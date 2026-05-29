import json
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GALLERY_DIR = ROOT / "docs" / "reference" / "gallery"
CSS_HREF = "../../../assets/templates"
sys.path.insert(0, str(ROOT / "scripts"))

from components.registry import render_component

TEMPLATE = (Path(__file__).parent / "gallery_template.html").read_text(encoding="utf-8")
SAMPLES = Path(__file__).parent / "golden_samples"


class _TagCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        self.count += 1

    def handle_startendtag(self, tag, attrs):
        self.count += 1


def count_tags(html: str) -> int:
    parser = _TagCounter()
    parser.feed(html)
    return parser.count


def build_one(theme_key: str, data: dict) -> str:
    sections = []
    for item in data["items"]:
        try:
            inner = render_component({"type": item["type"], "props": item["props"]})
        except Exception as e:
            inner = f'<div style="color:red;border:2px solid red;padding:8px">[渲染失败] {e}</div>'
        wrap_cls = item.get("wrap_class", "")
        sections.append(
            f'<div class="gallery-item">'
            f'<h3 class="gallery-item-label">{item["label"]} <code>&lt;{item["type"]}&gt;</code></h3>'
            f'<div class="gallery-render"><div class="{wrap_cls}">{inner}</div></div>'
            f'</div>'
        )
    return TEMPLATE.replace("{{ title }}", data["title"]).replace("{{ theme }}", data["theme"]).replace("{{ density }}", data["density"]).replace("{{ body }}", "\n".join(sections))


def ensure_assets():
    target = ROOT / "assets" / "templates"
    target.mkdir(parents=True, exist_ok=True)
    for name in ["_design-tokens.css", "_components.css"]:
        src = target / name
        dst = ROOT / "assets" / "templates" / name
        if src.exists() and src.resolve() != dst.resolve():
            shutil.copy2(src, dst)


def main():
    ensure_assets()
    data = json.loads((Path(__file__).parent / "gallery_data.json").read_text(encoding="utf-8"))
    for key in ["2b", "2c"]:
        if key in data:
            out_path = GALLERY_DIR / f"gallery-{key}.html"
            html = build_one(key, data[key])
            html = html.replace('href="assets/templates/', f'href="{CSS_HREF}/')
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            print(f"[OK] {out_path}")
    build_golden_gallery()


def build_golden_gallery():
    if not SAMPLES.exists():
        return
    sections = []
    for json_file in sorted(SAMPLES.glob("*.json")):
        sample = json_file.stem
        html_file = SAMPLES / f"{sample}.html"
        if not html_file.exists():
            continue
        expected = html_file.read_text(encoding="utf-8")
        input_data = json.loads(json_file.read_text(encoding="utf-8"))
        try:
            actual = render_component(input_data)
            status = "ok"
        except Exception as e:
            actual = f"<pre style='color:red'>渲染失败: {e}</pre>"
            status = "err"
        e_count = count_tags(expected)
        a_count = count_tags(actual)
        diff_msg = f"节点数 expected={e_count} actual={a_count}"
        if status == "ok" and e_count != a_count:
            status = "warn"
        sections.append(f"""
<div class="gallery-row">
  <h3>{sample} <span class="status {status}">{status}</span> <small>{diff_msg}</small></h3>
  <div class="gallery-split">
    <div class="gallery-side">
      <div class="gallery-label">真值(golden)</div>
      <div class="gallery-frame">{expected}</div>
    </div>
    <div class="gallery-side">
      <div class="gallery-label">renderer 输出</div>
      <div class="gallery-frame">{actual}</div>
    </div>
  </div>
</div>
""")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="2b" data-density="high"><head>
<meta charset="UTF-8"><title>Gallery</title>
<link rel="stylesheet" href="{CSS_HREF}/_design-tokens.css">
<link rel="stylesheet" href="{CSS_HREF}/_components.css">
<style>
body {{ font-family: 'HarmonyOS Sans', 'PingFang SC', sans-serif; padding: 24px; background: #f5f5f5; }}
.gallery-row {{ background: white; margin-bottom: 24px; padding: 16px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
.gallery-row h3 {{ margin-bottom: 12px; font-size: 16px; }}
.status {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: normal; }}
.status.ok {{ background: #d4edda; color: #155724; }}
.status.warn {{ background: #fff3cd; color: #856404; }}
.status.err {{ background: #f8d7da; color: #721c24; }}
.gallery-split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.gallery-side {{ border: 1px solid #ddd; border-radius: 4px; padding: 8px; overflow: auto; }}
.gallery-label {{ font-size: 12px; color: #888; margin-bottom: 8px; }}
.gallery-frame {{ background: white; padding: 8px; min-width: 560px; }}
</style></head><body>
<h1>Gallery - golden samples vs renderer 输出</h1>
{"".join(sections)}
</body></html>"""
    out = GALLERY_DIR / "gallery.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[OK] {out}")


if __name__ == "__main__":
    main()
