import copy
import json
import re
from pathlib import Path

import pytest

from scripts.components.registry import render_component
from scripts.components.tests.conftest import assert_component_cases, render_case


def test_basic():
    html = render_case("tob_journey_l1", 0)
    assert isinstance(html, str)


def test_second_case_and_escape():
    assert_component_cases("tob_journey_l1")


# ====== P8 修复回归保护(2026-05-25)======
# 这些 case 保护 tob_journey UML 路径的 fail-loud 行为 + slot 定位语义。
# 原 bug:未知 lane/stage/node 静默 continue,slot 仅排序不定位。

GOLDEN_DIR = Path(__file__).parent / "golden_samples"
SAMPLE = json.loads((GOLDEN_DIR / "tob_journey_l1_uml.json").read_text(encoding="utf-8"))


def test_bad_lane_raises_value_error():
    bad = copy.deepcopy(SAMPLE)
    bad["props"]["nodes"][0]["lane"] = "NONEXISTENT"
    with pytest.raises(ValueError, match=r"不存在的 lane"):
        render_component(bad)


def test_bad_stage_raises_value_error():
    bad = copy.deepcopy(SAMPLE)
    bad["props"]["nodes"][0]["stage"] = "NOSTAGE"
    with pytest.raises(ValueError, match=r"不存在的 stage"):
        render_component(bad)


def test_bad_edge_from_raises_value_error():
    bad = copy.deepcopy(SAMPLE)
    bad["props"]["edges"][0]["from"] = "n999"
    with pytest.raises(ValueError, match=r"不存在的 from node id"):
        render_component(bad)


def test_bad_edge_to_raises_value_error():
    bad = copy.deepcopy(SAMPLE)
    bad["props"]["edges"][0]["to"] = "n999"
    with pytest.raises(ValueError, match=r"不存在的 to node id"):
        render_component(bad)


def test_duplicate_slot_in_cell_raises_value_error():
    bad = copy.deepcopy(SAMPLE)
    # 把 l2/prepare cell 里两个 node 的 slot 都改成 0,触发重复
    for n in bad["props"]["nodes"]:
        if n["lane"] == "l2" and n["stage"] == "prepare":
            n["slot"] = 0
    with pytest.raises(ValueError, match=r"slot 重复"):
        render_component(bad)


def test_slot_value_drives_x_position():
    """slot 必须真正影响 x 定位(原 bug:slot 仅用于排序,位置由 enumerate idx 均分)。

    SAMPLE 已经满足密度门禁,所以不再缩减节点,只把一个特定节点改 label=A 用作探针,
    然后切换它的 slot 值,看 x 位置是否随之变化。
    """
    base = copy.deepcopy(SAMPLE)
    target = next(n for n in base["props"]["nodes"] if n["lane"] == "l1" and n["stage"] == "prepare" and int(n.get("slot", 0)) == 0)
    target["label"] = "ZZSLOTZZ"  # 独一无二的探针 label,正则提取用

    html0 = render_component(base)

    # 把 (l1, prepare) cell 内其他 slot 0 之外的节点先抢救一下(避免和 5 冲突),实际无影响
    target["slot"] = 5
    # 同 cell 若有 slot=5 的节点要 skip(SAMPLE 里 (l1,prepare) 只有 slot 0 和 1)
    html5 = render_component(base)

    def find_x(html: str) -> int:
        m = re.search(r'<g class="l1-node[^"]*"\s+transform="translate\((\d+)[^)]*\)">[\s\S]*?ZZSLOTZZ', html)
        assert m, "找不到 label=ZZSLOTZZ 的节点 transform"
        return int(m.group(1))

    x0 = find_x(html0)
    x5 = find_x(html5)
    assert x0 < x5, f"slot=5 的 x 应该大于 slot=0 的 x,实际 x0={x0} x5={x5}"
