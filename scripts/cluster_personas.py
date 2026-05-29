#!/usr/bin/env python3
"""
cluster_personas.py

R4/R5 范式下,基于受访者档位映射,聚类生成画像分组。

调用:
    python cluster_personas.py --workdir PATH

输入:
    02-classification.json(含 respondent_mapping)

输出:
    更新 02-classification.json 增加 groups 字段
    控制台输出聚类结果给模型展示给用户确认
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from path_utils import OUTPUT_ROOT_NAME, resolve_process_dir


def cluster_r4(classification: dict) -> list:
    """
    R4 聚类:基于 2 个变量的档位组合,直接 4 象限(或更少,如果某些组合无样本)。
    """
    variables = classification["value_variables"]
    mapping = classification["respondent_mapping"]

    if len(variables) != 2:
        raise ValueError("R4 需要恰好 2 个区分点")

    var1_key = variables[0]["key"]
    var2_key = variables[1]["key"]
    var1_name = variables[0]["name"]
    var2_name = variables[1]["name"]

    # 按象限聚类
    quadrants = defaultdict(list)
    for respondent, levels in mapping.items():
        v1 = levels[var1_key]
        v2 = levels[var2_key]
        quadrant_key = f"{var1_key}-{v1}_{var2_key}-{v2}"
        quadrants[quadrant_key].append(
            {"name": respondent, "v1": v1, "v2": v2}
        )

    groups = []
    for quadrant_key, members in quadrants.items():
        # 解析象限名
        parts = quadrant_key.split("_")
        v1_label = parts[0].split("-", 1)[1]
        v2_label = parts[1].split("-", 1)[1]
        groups.append(
            {
                "name": f"待命名({var1_name}-{v1_label} × {var2_name}-{v2_label})",
                "quadrant": quadrant_key,
                "members": [m["name"] for m in members],
                "level_signature": {
                    var1_key: v1_label,
                    var2_key: v2_label,
                },
            }
        )

    return groups


def cluster_r5(classification: dict) -> list:
    """
    R5 聚类:基于多变量的档位组合相似度,聚成 K 类。

    简单规则:
    - 把每位受访者的档位组合做"指纹"
    - 指纹完全相同的人聚一类
    - 简化:只做完全相同聚类,后续让模型基于此再调整(允许档位略有差异的合并)
    """
    variables = classification["value_variables"]
    mapping = classification["respondent_mapping"]

    var_keys = [v["key"] for v in variables]

    # 把每位受访者的档位组合做"指纹"
    fingerprints = defaultdict(list)
    for respondent, levels in mapping.items():
        fingerprint = tuple(levels[k] for k in var_keys)
        fingerprints[fingerprint].append(respondent)

    groups = []
    for idx, (fingerprint, members) in enumerate(fingerprints.items()):
        signature = {k: fingerprint[i] for i, k in enumerate(var_keys)}
        groups.append(
            {
                "name": f"待命名(组 {idx + 1})",
                "cluster_id": f"cluster-{idx + 1}",
                "members": members,
                "level_signature": signature,
            }
        )

    return groups


def format_for_user(groups: list, classification: dict) -> str:
    """
    把聚类结果格式化成给用户看的中文展示。
    """
    paradigm = classification.get("paradigm", "R4")
    variables = classification["value_variables"]
    var_name_map = {v["key"]: v["name"] for v in variables}

    lines = [f"基于档位映射,聚出 {len(groups)} 类画像:\n"]

    for g in groups:
        lines.append(f"【{g['name']}】({len(g['members'])} 人:{'、'.join(g['members'])})")
        for var_key, level in g["level_signature"].items():
            var_name = var_name_map.get(var_key, var_key)
            lines.append(f"  - {var_name}:{level}")
        lines.append("")

    lines.append("这个分类你认可吗?")
    lines.append("- 认可")
    lines.append("- 给某个画像重命名")
    lines.append("- 调整某位受访者的归属")
    lines.append("- 拆分/合并某类")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workdir",
        default=OUTPUT_ROOT_NAME,
        help="项目运行目录或过程稿目录",
    )
    args = parser.parse_args()

    workdir = resolve_process_dir(Path(args.workdir))
    classification_file = workdir / "02-classification.json"

    if not classification_file.exists():
        print(f"错误:{classification_file} 不存在")
        return 2

    with open(classification_file, "r", encoding="utf-8") as f:
        classification = json.load(f)

    paradigm = classification.get("paradigm", "R4")

    if paradigm == "R4":
        try:
            groups = cluster_r4(classification)
        except ValueError as exc:
            print(f"错误:{exc}")
            return 2
    elif paradigm == "R5":
        groups = cluster_r5(classification)
    else:
        print(f"错误:聚类只支持 R4/R5,当前 paradigm = {paradigm}")
        return 2

    classification["groups"] = groups

    with open(classification_file, "w", encoding="utf-8") as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    # 输出给模型展示给用户的内容
    print(format_for_user(groups, classification))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
