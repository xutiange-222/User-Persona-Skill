"""各组件 renderer 冒烟测试（合并自 20+ 个单文件 test_*.py）。"""
from __future__ import annotations

import pytest

from scripts.components.tests.conftest import CASES, assert_component_cases, render_case

SMOKE_COMPONENT_TYPES = sorted(CASES.keys())
# 无图时不渲染,合法输出为空字符串
ALLOW_EMPTY_TYPES = {"detail_illust_corner"}


@pytest.mark.parametrize("component_type", SMOKE_COMPONENT_TYPES)
def test_renderer_smoke_basic(component_type: str):
    html = render_case(component_type, 0)
    assert isinstance(html, str)
    if component_type not in ALLOW_EMPTY_TYPES:
        assert html.strip()


@pytest.mark.parametrize("component_type", SMOKE_COMPONENT_TYPES)
def test_renderer_smoke_second_case_no_script(component_type: str):
    assert_component_cases(component_type)
