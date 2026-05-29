"""
merge.py — 把同一分组(同一角色)的多份单文档抽取结果合并成一个画像

合并规则参考 references/schema-tob.md 的「多文档合并时的处理」段落:
- 共性字段(basic_profile, knowledge_background, collaboration):取多份的高频项
- 列表字段(pain_points, scenarios, representative_quotes):合并去重
- 比例字段(responsibilities):取均值后归一化到 100%
- 冲突在 description 里标注

用法:
    python merge.py \\
        --input-dir <workdir>/extracted/<group>/ \\
        --output <workdir>/personas/<group>.json \\
        --persona-name <角色名> \\
        --schema toB
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logger = logging.getLogger("merge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_extracted_files(input_dir: Path) -> list:
    """加载目录下所有 .json 文件"""
    files = sorted(input_dir.glob("*.json"))
    if not files:
        logger.error(f"目录 {input_dir} 下没有 JSON 文件")
        sys.exit(1)

    results = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                results.append(json.load(fp))
        except Exception as e:
            logger.error(f"读取 {f} 失败: {e},跳过")
    return results


def majority_vote(values: list, label: str = "") -> str:
    """对字符串列表取多数。返回多数值,如果有冲突在末尾标注"""
    # 过滤掉「文档未提及」
    valid = [v for v in values if v and v != "文档未提及"]
    if not valid:
        return "文档未提及"

    counter = Counter(valid)
    most_common = counter.most_common()
    if len(most_common) == 1:
        return most_common[0][0]

    top_value, top_count = most_common[0]
    # 如果存在并列或显著差异,加注释
    if top_count == most_common[1][1]:
        # 平票
        return f"{top_value}(存在差异:{', '.join(v for v, _ in most_common[:3])})"
    return top_value


def merge_dict_field(items: list, field_name: str) -> dict:
    """合并 dict 类型字段(如 basic_profile)"""
    sub_dicts = [item.get(field_name, {}) for item in items if item.get(field_name)]
    if not sub_dicts:
        return {}

    # 收集所有 sub_keys
    all_keys = set()
    for d in sub_dicts:
        all_keys.update(d.keys())

    merged = {}
    for key in all_keys:
        values = [d.get(key, "") for d in sub_dicts if d.get(key)]
        merged[key] = majority_vote(values, label=f"{field_name}.{key}")
    return merged


def merge_responsibilities(items: list) -> list:
    """合并职责占比:把所有 task 收集,相同 task 取均值,归一化到 100"""
    all_tasks = []
    for item in items:
        resp = item.get("responsibilities", [])
        for r in resp:
            all_tasks.append((r.get("task", ""), r.get("percentage", 0)))

    if not all_tasks:
        return []

    # 简单聚合:按 task 名相似度合并(MVP 用精确匹配,后续可加模糊匹配)
    task_groups = {}
    for task, pct in all_tasks:
        key = task.strip()
        task_groups.setdefault(key, []).append(pct)

    # 取每组均值
    aggregated = [
        {"task": task, "percentage": sum(pcts) / len(pcts)}
        for task, pcts in task_groups.items()
    ]
    # 按 percentage 降序排
    aggregated.sort(key=lambda x: x["percentage"], reverse=True)
    # 取 top 3
    aggregated = aggregated[:3]

    # 归一化到 100
    total = sum(a["percentage"] for a in aggregated)
    if total > 0:
        for a in aggregated:
            a["percentage"] = round(a["percentage"] / total * 100)
        # 修正四舍五入误差
        diff = 100 - sum(a["percentage"] for a in aggregated)
        if aggregated:
            aggregated[0]["percentage"] += diff

    return aggregated


def merge_list_field(items: list, field_name: str, dedup_key: str = None) -> list:
    """合并列表字段,可选去重"""
    merged = []
    seen = set()
    for item in items:
        for entry in item.get(field_name, []):
            if dedup_key and isinstance(entry, dict):
                key = entry.get(dedup_key, "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
            elif isinstance(entry, str):
                if entry in seen:
                    continue
                seen.add(entry)
            merged.append(entry)
    return merged


def merge_personas(items: list, persona_name: str = None) -> dict:
    """主合并函数"""
    if len(items) == 1:
        # 单文档场景:直接返回,补一些元数据
        result = dict(items[0])
        result["user_count"] = 1
        if persona_name:
            result["name"] = persona_name
        result["source_documents"] = [items[0].get("_source_file", "unknown")]
        # 清理内部字段
        result.pop("_source_file", None)
        return result

    # 多文档合并
    merged = {
        "persona_type": items[0].get("persona_type", "toB"),
        "user_count": len(items),
        "source_documents": [item.get("_source_file", f"doc_{i}") for i, item in enumerate(items)],
    }

    # name 用传入的 persona_name,否则用第一份的
    merged["name"] = persona_name or items[0].get("name", "未命名画像")

    # description:合并多份的简短摘要
    descriptions = [item.get("description", "") for item in items if item.get("description")]
    if descriptions:
        # 用第一份作为基础,如果有显著差异在末尾标注
        merged["description"] = descriptions[0]
        if len(set(descriptions)) > 1:
            merged["description"] += f"(合并自 {len(descriptions)} 份访谈)"

    # 各字段合并
    if any("basic_profile" in item for item in items):
        merged["basic_profile"] = merge_dict_field(items, "basic_profile")

    if any("knowledge_background" in item for item in items):
        merged["knowledge_background"] = merge_dict_field(items, "knowledge_background")

    if any("collaboration" in item for item in items):
        merged["collaboration"] = merge_dict_field(items, "collaboration")

    if any("responsibilities" in item for item in items):
        merged["responsibilities"] = merge_responsibilities(items)

    # 列表字段
    if any("scenarios" in item for item in items):
        merged["scenarios"] = merge_list_field(items, "scenarios", dedup_key="scenario")

    if any("experience_goals" in item for item in items):
        merged["experience_goals"] = merge_list_field(items, "experience_goals")

    if any("pain_points" in item for item in items):
        merged["pain_points"] = merge_list_field(items, "pain_points")

    if any("representative_quotes" in item for item in items):
        merged["representative_quotes"] = merge_list_field(items, "representative_quotes")

    # one_sentence_need:取所有 quotes 里第一份的
    needs = [item.get("one_sentence_need", "") for item in items if item.get("one_sentence_need")]
    if needs:
        merged["one_sentence_need"] = needs[0]

    # 自定义字段(用户在对齐阶段加的):
    # 检测每份 item 里出现但不在标准字段集里的 key
    standard_keys = {
        "name", "description", "user_count", "persona_type", "source_documents",
        "basic_profile", "knowledge_background", "responsibilities",
        "collaboration", "scenarios", "experience_goals", "pain_points",
        "one_sentence_need", "representative_quotes", "_source_file",
    }
    custom_keys = set()
    for item in items:
        for k in item.keys():
            if k not in standard_keys:
                custom_keys.add(k)
    for ck in custom_keys:
        values = [item.get(ck) for item in items if item.get(ck)]
        if not values:
            continue
        # 列表 → 合并去重
        if all(isinstance(v, list) for v in values):
            seen = set()
            merged_list = []
            for v in values:
                for entry in v:
                    key = entry if isinstance(entry, str) else json.dumps(entry, ensure_ascii=False)
                    if key not in seen:
                        seen.add(key)
                        merged_list.append(entry)
            merged[ck] = merged_list
        # dict → 合并子字段
        elif all(isinstance(v, dict) for v in values):
            merged[ck] = merge_dict_field(items, ck)
        # 字符串 → 多数表决
        else:
            merged[ck] = majority_vote([str(v) for v in values])

    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="extracted/<group>/ 目录")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--persona-name", help="角色名(可选)")
    parser.add_argument("--schema", default="toB", choices=["toB", "toC"])
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    items = load_extracted_files(input_dir)
    logger.info(f"加载到 {len(items)} 份抽取结果")

    merged = merge_personas(items, persona_name=args.persona_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ 合并完成: {output_path}")
    print(json.dumps({"success": True, "output": str(output_path), "merged_count": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
