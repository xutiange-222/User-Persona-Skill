#!/usr/bin/env python3
"""裁切头像/场景图并写入说明书样例报告的 assets/。

若 assets/sample-sources/ 无合成源图，会自动生成占位合成条（维护用，非真实截图）。
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

V9 = Path(__file__).resolve().parents[2]
SRC = V9 / "assets" / "sample-sources"

SAMPLE_DIRS = [
    V9 / "docs/reference/reports/A-单画像/2B-保障型运维工程师",
    V9 / "docs/reference/reports/A-单画像/2C-内行场景派",
    V9 / "docs/reference/reports/B-多角色/2B-DevOps五角色",
    V9 / "docs/reference/reports/D-二维矩阵/2C-HiRes-2维",
    V9 / "docs/reference/reports/D-二维矩阵/2B-电力调度员",
    V9 / "docs/reference/reports/E-多维分布/2C-HiRes-多区分点",
]

B2_PERSONAS = [
    "保障型运维工程师",
    "运维配置管理者",
    "测试体系管理者",
    "一线测试负责人",
    "交付型SM",
]

C2_PERSONAS = [
    "内行场景派",
    "感知场景派",
    "优惠深听派",
    "认价检索派",
    "实惠助眠派",
]

POWER_PERSONAS = [
    "转供演算派",
    "网架研判派",
    "消纳统筹派",
    "现场协同派",
]

B2_COLORS = ["#3D5A80", "#4A6741", "#7A5C3E", "#6B4C7A", "#2C698D"]
C2_COLORS = ["#5B8CAA", "#6B9B6E", "#D4894A", "#C9A227", "#B85C5C"]
POWER_COLORS = ["#3E5C76", "#4F6D7A", "#5C7A52", "#8B7355"]

SCREENSHOTS = [
    ("hires-试听专区.png", 0),
    ("hires-分类.png", 1),
    ("hires-排行榜.png", 2),
    ("hires-歌单详情.png", 3),
    ("hires-播放页.png", 4),
]

PHONE_LABELS = ["试听专区", "分类", "排行榜", "歌单详情", "播放页"]
PHONE_UI_COLORS = ["#1A1A2E", "#162447", "#1F4068", "#1B262C", "#222831"]

MOCKUP_MAP = {
    "场景歌单": "hires-歌单详情.png",
    "专辑介绍": "hires-播放页.png",
    "试听区": "hires-试听专区.png",
    "分类": "hires-分类.png",
    "排行榜": "hires-排行榜.png",
    "会员页": "hires-试听专区.png",
    "搜索": "hires-分类.png",
    "离线播放": "hires-播放页.png",
    "古典热榜": "hires-排行榜.png",
    "活动页": "hires-试听专区.png",
    "音质对比": "hires-播放页.png",
}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def _draw_avatar_cell(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], name: str, color: str) -> None:
    x0, y0, x1, y1 = box
    base = _hex_rgb(color)
    light = tuple(min(255, c + 35) for c in base)
    for y in range(y0, y1):
        t = (y - y0) / max(y1 - y0, 1)
        row = tuple(int(base[i] * (1 - t) + light[i] * t) for i in range(3))
        draw.line([(x0, y), (x1, y)], fill=row)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    r = min(x1 - x0, y1 - y0) // 5
    draw.ellipse([cx - r, cy - r - 20, cx + r, cy + r - 20], fill=(255, 255, 255, 60))
    draw.ellipse([cx - r * 1.4, cy + 10, cx + r * 1.4, cy + r * 2.8], fill=(255, 255, 255, 45))
    glyph = name[0]
    font = _font(max(28, (x1 - x0) // 4))
    bbox = draw.textbbox((0, 0), glyph, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 10), glyph, fill="white", font=font)


def render_avatar_png(name: str, color: str, size: tuple[int, int] = (320, 420)) -> Image.Image:
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    _draw_avatar_cell(draw, (0, 0, size[0], size[1]), name, color)
    return im


def render_b2_sheet() -> Image.Image:
    w, h = 900, 600
    im = Image.new("RGB", (w, h), "#E8ECF0")
    draw = ImageDraw.Draw(im)
    cols, rows = 3, 2
    cw, ch = w // cols, h // rows
    cells = [(0, 0), (1, 0), (2, 0), (1, 1), (2, 1)]
    for (col, row), name, color in zip(cells, B2_PERSONAS, B2_COLORS):
        box = (col * cw + 8, row * ch + 8, (col + 1) * cw - 8, (row + 1) * ch - 8)
        _draw_avatar_cell(draw, box, name, color)
    return im


def render_c2_row_sheet(count: int, names: list[str], colors: list[str]) -> Image.Image:
    w, h = 300 * count, 420
    im = Image.new("RGB", (w, h), "#EEF2F5")
    draw = ImageDraw.Draw(im)
    cw = w // count
    for i, (name, color) in enumerate(zip(names, colors)):
        box = (i * cw + 6, 6, (i + 1) * cw - 6, h - 6)
        _draw_avatar_cell(draw, box, name, color)
    return im


def render_c2_grid_sheet() -> Image.Image:
    w, h = 600, 600
    im = Image.new("RGB", (w, h), "#EEF2F5")
    draw = ImageDraw.Draw(im)
    cw, ch = w // 2, h // 2
    placements = [((1, 0), C2_PERSONAS[3], C2_COLORS[3]), ((0, 1), C2_PERSONAS[4], C2_COLORS[4])]
    for (col, row), name, color in placements:
        box = (col * cw + 6, row * ch + 6, (col + 1) * cw - 6, (row + 1) * ch - 6)
        _draw_avatar_cell(draw, box, name, color)
    return im


def render_phone_strip() -> Image.Image:
    w, h = 1680, 850
    im = Image.new("RGB", (w, h), "#0F1115")
    draw = ImageDraw.Draw(im)
    boxes = [
        (21, 68, 308, 778),
        (323, 68, 606, 778),
        (626, 68, 920, 778),
        (941, 68, 1273, 778),
        (1292, 68, 1647, 778),
    ]
    for box, label, ui in zip(boxes, PHONE_LABELS, PHONE_UI_COLORS):
        x0, y0, x1, y1 = box
        draw.rounded_rectangle(box, radius=18, fill=ui, outline="#444", width=2)
        draw.rectangle([x0 + 12, y0 + 36, x1 - 12, y1 - 48], fill="#FFFFFF")
        title_font = _font(22)
        draw.text((x0 + 24, y0 + 52), label, fill="#333", font=title_font)
        draw.rectangle([x0 + 24, y0 + 100, x1 - 24, y0 + 180], fill="#E8EDF2")
        draw.rectangle([x0 + 24, y0 + 200, x1 - 24, y0 + 280], fill="#DDE4EA")
        draw.rectangle([x0 + 24, y0 + 300, x1 - 24, y1 - 80], fill="#F4F6F8")
    return im


def _png_sources() -> list[Path]:
    return sorted(p for p in SRC.glob("*.png") if p.is_file())


def _is_phone_source(name: str) -> bool:
    return any(k in name for k in ("手机", "截图", "5屏", "phones", "screen"))


def _is_c2_avatar_source(name: str) -> bool:
    return name.startswith("2C") and not _is_phone_source(name) and (
        "头像" in name or name.startswith("2C-3") or name.startswith("2C-4")
    )


def find_b2_sheet() -> Path:
    for p in _png_sources():
        if p.name.upper().startswith("2B"):
            return p
    raise FileNotFoundError(f"missing 2B avatar sheet in {SRC}")


def find_c2_avatar_sheets() -> tuple[Path | None, Path | None]:
    c3 = sorted(p for p in _png_sources() if p.name.startswith("2C-3"))
    c4 = sorted(p for p in _png_sources() if p.name.startswith("2C-4"))
    single = sorted(p for p in _png_sources() if _is_c2_avatar_source(p.name))
    if c3 and c4:
        return c3[0], c4[0]
    if single:
        return single[0], None
    raise FileNotFoundError(f"missing 2C avatar sheet in {SRC}")


def find_phone_sheet() -> Path:
    for p in _png_sources():
        if p.name.upper().startswith("2C") and _is_phone_source(p.name):
            return p
    for p in _png_sources():
        if p.name.upper().startswith("2C") and not _is_c2_avatar_source(p.name):
            return p
    raise FileNotFoundError(f"missing 2C phone strip in {SRC}")


def ensure_sample_sources() -> None:
    """仅当目录里完全没有 PNG 时才生成占位合成条。"""
    SRC.mkdir(parents=True, exist_ok=True)
    if _png_sources():
        return
    save_png(render_b2_sheet(), SRC / "2B-sample-sources.png")
    save_png(render_c2_row_sheet(3, C2_PERSONAS[:3], C2_COLORS[:3]), SRC / "2C-3-sample-sources.png")
    save_png(render_c2_grid_sheet(), SRC / "2C-4-sample-sources.png")
    save_png(render_phone_strip(), SRC / "2C-hires-phones.png")
    print(f"generated placeholder sheets in {SRC}")


def crop_grid(path: Path, cols: int, rows: int, cells: list[tuple[int, int]]) -> list[Image.Image]:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    cw, ch = w // cols, h // rows
    out = []
    for col, row in cells:
        box = (col * cw, row * ch, (col + 1) * cw, (row + 1) * ch)
        out.append(im.crop(box))
    return out


def crop_row(path: Path, n: int) -> list[Image.Image]:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    cw = w // n
    return [im.crop((i * cw, 0, (i + 1) * cw, h)) for i in range(n)]


def is_bg_pixel(r: int, g: int, b: int) -> bool:
    """合成图里的棋盘格/留白底（非人物皮肤阴影）。"""
    return r > 180 and g > 180 and b > 180 and max(r, g, b) - min(r, g, b) < 25


def is_removable_neutral(r: int, g: int, b: int, *, allow_bright: bool = False) -> bool:
    if max(r, g, b) - min(r, g, b) > 20:
        return False
    avg = (r + g + b) / 3
    if avg < 170:
        return False
    if not allow_bright and avg >= 252:
        return False
    return True


def flood_edge_transparent(im: Image.Image, tol: int = 22) -> Image.Image:
    """从四边泛洪移除贴边的中性灰/棋盘格底。"""
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    data = im.load()
    edge_refs = [
        im.getpixel((0, 0))[:3],
        im.getpixel((w - 1, 0))[:3],
        im.getpixel((0, h - 1))[:3],
        im.getpixel((w - 1, h - 1))[:3],
    ]

    def similar_bg(r: int, g: int, b: int) -> bool:
        return any(
            abs(r - rr) <= tol and abs(g - rg) <= tol and abs(b - rb) <= tol
            for rr, rg, rb in edge_refs
        )

    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        if (x, y) in seen or x < 0 or y < 0 or x >= w or y >= h:
            continue
        r, g, b, a = data[x, y]
        if a == 0:
            seen.add((x, y))
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            continue
        on_edge = x == 0 or y == 0 or x == w - 1 or y == h - 1
        if not is_removable_neutral(r, g, b, allow_bright=on_edge):
            continue
        if not on_edge and not similar_bg(r, g, b):
            continue
        seen.add((x, y))
        data[x, y] = (r, g, b, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def peel_adjacent_checkerboard(im: Image.Image, max_passes: int = 16) -> Image.Image:
    im = im.convert("RGBA")
    for _ in range(max_passes):
        data = im.load()
        w, h = im.size
        to_clear: list[tuple[int, int]] = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = data[x, y]
                if a == 0 or not is_removable_neutral(r, g, b):
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and data[nx, ny][3] == 0:
                        to_clear.append((x, y))
                        break
        if not to_clear:
            break
        for x, y in to_clear:
            r, g, b, _ = data[x, y]
            data[x, y] = (r, g, b, 0)
    return im


def remove_interior_neutral_pockets(im: Image.Image, max_size: int = 12000) -> Image.Image:
    """移除人物内部小型中性灰/棋盘格内孔（如眼镜、手指缝）。"""
    from collections import deque

    im = im.convert("RGBA")
    w, h = im.size
    data = im.load()
    seen: set[tuple[int, int]] = set()

    for y in range(h):
        for x in range(w):
            if (x, y) in seen:
                continue
            r, g, b, a = data[x, y]
            if a == 0 or not is_removable_neutral(r, g, b, allow_bright=True):
                continue
            comp: list[tuple[int, int]] = []
            touches_border = False
            q: deque[tuple[int, int]] = deque([(x, y)])
            while q:
                cx, cy = q.popleft()
                if (cx, cy) in seen:
                    continue
                if cx < 0 or cy < 0 or cx >= w or cy >= h:
                    continue
                cr, cg, cb, ca = data[cx, cy]
                if ca == 0 or not is_removable_neutral(cr, cg, cb, allow_bright=True):
                    continue
                seen.add((cx, cy))
                comp.append((cx, cy))
                if cx == 0 or cy == 0 or cx == w - 1 or cy == h - 1:
                    touches_border = True
                q.extend(((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)))
            if not touches_border and len(comp) <= max_size:
                for cx, cy in comp:
                    cr, cg, cb, _ = data[cx, cy]
                    data[cx, cy] = (cr, cg, cb, 0)
    return im


def _bg_gutters(length: int, bg_ratios: list[float], thr: float = 0.92, min_gutter: int = 5) -> list[tuple[int, int]]:
    gutters: list[tuple[int, int]] = []
    i = 0
    while i < length:
        if bg_ratios[i] >= thr:
            start = i
            while i < length and bg_ratios[i] >= thr:
                i += 1
            if i - start >= min_gutter:
                gutters.append((start, i))
        else:
            i += 1
    return gutters


def detect_2x2_boxes(im: Image.Image) -> list[tuple[int, int, int, int]]:
    """按合成图留白缝自动切 2×2 四格（适配 2C头像-4人 类横拼）。"""
    rgb = im.convert("RGB")
    w, h = im.size
    col_bg = [sum(is_bg_pixel(*rgb.getpixel((x, y))) for y in range(h)) / h for x in range(w)]
    row_bg = [sum(is_bg_pixel(*rgb.getpixel((x, y))) for x in range(w)) / w for y in range(h)]
    vg = _bg_gutters(w, col_bg)
    hg = _bg_gutters(h, row_bg)
    if len(vg) >= 3 and len(hg) >= 3:
        return [
            (vg[0][1], hg[0][1], vg[1][0], hg[1][0]),
            (vg[1][1], hg[0][1], vg[2][0], hg[1][0]),
            (vg[0][1], hg[1][1], vg[1][0], hg[2][0]),
            (vg[1][1], hg[1][1], vg[2][0], hg[2][0]),
        ]
    cw, ch = w // 2, h // 2
    return [(0, 0, cw, ch), (cw, 0, w, ch), (0, ch, cw, h), (cw, ch, w, h)]


def process_avatar_crop(im: Image.Image) -> Image.Image:
    im = flood_edge_transparent(im)
    im = peel_adjacent_checkerboard(im)
    return remove_interior_neutral_pockets(im)


def _phone_crop_boxes(w: int, h: int) -> list[tuple[int, int, int, int]]:
    """按 HiRes 五屏横拼真值坐标等比缩放（参考画布 1680×850）。"""
    ref_w, ref_h = 1680, 850
    ref_boxes = [
        (21, 68, 308, 778),
        (323, 68, 606, 778),
        (626, 68, 920, 778),
        (941, 68, 1273, 778),
        (1292, 68, 1647, 778),
    ]
    sx, sy = w / ref_w, h / ref_h
    return [
        (int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy))
        for x0, y0, x1, y1 in ref_boxes
    ]


def crop_c2_avatars(path: Path, companion: Path | None, b2_sheet: Path | None = None) -> list[Image.Image]:
    if companion is not None:
        crops = crop_row(path, 3) + crop_grid(companion, 2, 2, [(1, 0), (0, 1)])
        return [process_avatar_crop(c) for c in crops]

    im = Image.open(path).convert("RGBA")
    boxes = detect_2x2_boxes(im)
    crops = [process_avatar_crop(im.crop(box)) for box in boxes]
    if len(crops) == 4 and len(C2_PERSONAS) == 5:
        if b2_sheet is not None:
            extra = crop_grid(b2_sheet, 3, 2, [(0, 1)])[0]
            crops.append(process_avatar_crop(extra))
        else:
            crops.append(crops[-1].copy())
    return crops[: len(C2_PERSONAS)]


def crop_phone_strip(path: Path, n: int, phone_ratio: float = 0.78) -> list[Image.Image]:
    if n == 5:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        return [im.crop(box) for box in _phone_crop_boxes(w, h)]
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw = w // n
    phone_h = int(h * phone_ratio)
    return [im.crop((i * cw, 0, (i + 1) * cw, phone_h)) for i in range(n)]


def save_png(img: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if img.mode == "RGBA":
        img.save(dest, "PNG")
    else:
        img.convert("RGB").save(dest, "PNG", optimize=True)


def build_crops(out_assets: Path) -> dict[str, Path]:
    avatar_dir = out_assets / "画像头像素材"
    shot_dir = out_assets / "界面截图"
    if out_assets.exists():
        shutil.rmtree(out_assets)
    avatar_dir.mkdir(parents=True)
    shot_dir.mkdir(parents=True)

    b2_sheet = find_b2_sheet()
    b2_cells = [(0, 0), (1, 0), (2, 0), (1, 1), (2, 1)]
    for name, cell in zip(B2_PERSONAS, crop_grid(b2_sheet, 3, 2, b2_cells)):
        save_png(process_avatar_crop(cell), avatar_dir / f"{name}.png")

    c2_primary, c2_secondary = find_c2_avatar_sheets()
    for name, cell in zip(C2_PERSONAS, crop_c2_avatars(c2_primary, c2_secondary, b2_sheet)):
        save_png(cell, avatar_dir / f"{name}.png")

    b2_extra = process_avatar_crop(crop_grid(b2_sheet, 3, 2, [(0, 1)])[0])
    for name, cell in zip(
        POWER_PERSONAS,
        [b2_extra, *[process_avatar_crop(c) for c in crop_grid(b2_sheet, 3, 2, [(0, 0), (1, 0), (2, 0)])[:3]]],
    ):
        save_png(cell, avatar_dir / f"{name}.png")

    phone_sheet = find_phone_sheet()
    for fname, idx in SCREENSHOTS:
        save_png(crop_phone_strip(phone_sheet, 5)[idx], shot_dir / fname)

    return {p.name: p for p in avatar_dir.glob("*.png")} | {p.name: p for p in shot_dir.glob("*.png")}


def patch_2b_avatar(html: str, persona_file: str, persona_name: str) -> str:
    img = (
        f'<img class="persona-avatar" src="assets/画像头像素材/{persona_name}.png" '
        f'alt="{persona_name}">'
    )
    for sid in (f"{persona_file}-core", persona_file):
        pattern = (
            rf'(<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>.*?'
            rf'<div class="avatar-wrap">)(?:<div class="persona-avatar placeholder">[^<]*</div>|<img class="persona-avatar"[^>]*>)'
        )
        html, n = re.subn(pattern, rf"\1{img}", html, count=1, flags=re.DOTALL)
        if n:
            break
    return html


def patch_2c_illust(html: str, persona_idx: int, persona_name: str) -> str:
    img = (
        f'<img class="persona-illust" src="assets/画像头像素材/{persona_name}.png" '
        f'alt="{persona_name}">'
    )
    for pid in (f"persona-{persona_idx}", f"persona-{persona_idx}-journey"):
        pattern = (
            rf'(<section class="persona-slide[^"]*" id="{re.escape(pid)}"[^>]*>.*?'
            rf')(?:<div class="persona-illust-placeholder">[^<]*</div>|<img class="persona-illust"[^>]*>)'
        )
        html = re.sub(pattern, rf"\1{img}", html, count=1, flags=re.DOTALL)
    return html


def patch_mockups(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        label = m.group(1).strip()
        shot = MOCKUP_MAP.get(label)
        if not shot:
            return m.group(0)
        return (
            f'<div class="mockup-frame mockup-frame--has-img"><img class="mockup-img" '
            f'src="assets/界面截图/{shot}" alt=""></div>'
        )

    return re.sub(
        r'<div class="mockup-frame">📱<br>([^<]+)</div>',
        repl,
        html,
    )


def patch_report(report_dir: Path, mode: str) -> None:
    report = report_dir / "report.html"
    if not report.exists():
        return
    html = report.read_text(encoding="utf-8")

    if mode == "2b-single":
        html = patch_2b_avatar(html, "persona-1", "保障型运维工程师")
    elif mode == "2b-full":
        for i, name in enumerate(B2_PERSONAS, start=1):
            html = patch_2b_avatar(html, f"persona-{i}", name)
    elif mode == "2b-power":
        for i, name in enumerate(POWER_PERSONAS, start=1):
            html = patch_2b_avatar(html, f"persona-{i}", name)
    elif mode == "2c-single":
        html = patch_2c_illust(html, 1, "内行场景派")
        html = patch_mockups(html)
    elif mode == "2c-full":
        for i, name in enumerate(C2_PERSONAS, start=1):
            html = patch_2c_illust(html, i, name)
        html = patch_mockups(html)

    report.write_text(html, encoding="utf-8")


def refresh_default_avatars_from_staging(staging: Path) -> None:
    """样例裁切完成后，把 staging 头像合并进 skill 默认库。"""
    src = staging / "画像头像素材"
    dest = V9 / "assets" / "default-avatars"
    dest.mkdir(parents=True, exist_ok=True)
    if not src.is_dir():
        return
    for png in src.glob("*.png"):
        shutil.copy2(png, dest / png.name)


def main() -> None:
    ensure_sample_sources()

    staging = V9 / "_sample_assets_staging"
    build_crops(staging)
    refresh_default_avatars_from_staging(staging)

    modes = ["2b-single", "2c-single", "2b-full", "2c-full", "2b-power", "2c-full"]
    targets = list(zip(SAMPLE_DIRS, modes))

    for report_dir, mode in targets:
        assets = report_dir / "assets"
        if assets.exists():
            shutil.rmtree(assets)
        shutil.copytree(staging, assets)
        patch_report(report_dir, mode)
        print(f"patched {report_dir.relative_to(V9)} ({mode})")

    shutil.rmtree(staging)
    tmp = V9 / "_tmp_assets_preview"
    if tmp.exists():
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
