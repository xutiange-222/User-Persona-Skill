"""
reduce_field.py — 逐字段语义聚合

把 N 份单文档抽取的同字段内容,通过模型做语义聚类,产出:
- 合并后的字段值(去重 + 同义合并)
- 每个观点带 mention_count(N/M)和 mentioned_by(哪几位提过)

不同字段类型用不同的 reducer prompt(在 assets/prompts/reduce_*.txt)。

用法:
    python reduce_field.py \\
        --field <field_name> \\
        --inputs <extracted/*.json glob> \\
        --output <reduced JSON 片段路径>

环境变量(继承自 cc switch 配置):
    ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_MODEL
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests

logger = logging.getLogger("reduce_field")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-opus-4-5"
PROMPTS_DIR = Path(__file__).parent.parent / "assets" / "prompts"
SHARED_CONTRACT_PATH = PROMPTS_DIR / "_shared-language-contract.txt"

_PRIVACY_P0_BLOCK = """
## P0 脱敏(最强约束,与 SKILL.md 约束 8 同级)
- 聚合后的 title/detail/正文描述中**禁止出现访谈真名**(如刘宇、刘军、完整文件名)。
- mentioned_by 与 evidence 的 source 只用抽取产物中的稳定匿名 _source_id，例如 P12AB34CD。
- 禁止在一条描述里用真名对比多人;用「部分受访者」「该类型用户」或脱敏指代。
"""

# 字段 → reducer prompt 文件
FIELD_REDUCER_PROMPT = {
    "responsibilities": "reduce_responsibilities.txt",
    "pain_points": "reduce_titled_list.txt",
    "experience_goals": "reduce_titled_list.txt",
    "kpi": "reduce_string_list.txt",
    "main_tasks": "reduce_string_list.txt",
    "collaboration": "reduce_collaboration.txt",
    "business_systems": "reduce_system_list.txt",
    "ai_assist_systems": "reduce_system_list.txt",
    "fault_scenarios": "reduce_titled_list.txt",
    "scenarios": "reduce_scenario_list.txt",
    "high_freq_tasks": "reduce_titled_list.txt",
    "basic_profile": "reduce_basic_profile.txt",
    "knowledge_background": "reduce_basic_profile.txt",
    "representative_quotes": "reduce_quotes.txt",
    "one_sentence_need": "reduce_one_sentence.txt",
}


def call_model(prompt: str, max_retries: int = 1) -> str:
    base_url = os.environ.get("ANTHROPIC_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    if not auth_token:
        raise ValueError("环境变量 ANTHROPIC_AUTH_TOKEN 未设置")

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{base_url}/v1/messages",
                headers={
                    "x-api-key": auth_token,
                    "Authorization": f"Bearer {auth_token}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=180,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except (requests.RequestException, KeyError) as e:
            if attempt < max_retries:
                logger.warning(f"调用失败 (attempt {attempt+1}): {e},重试中...")
                time.sleep(2)
            else:
                raise


def extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # 找第一个 [ 或 { 到对应的 ]/}
    for open_c, close_c in [("[", "]"), ("{", "}")]:
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
    raise ValueError(f"无法从模型返回中提取 JSON: {text[:300]}")


def load_extractions(input_paths: list) -> list:
    """加载多份抽取结果"""
    extractions = []
    normalized = sorted({str(Path(p).resolve()) for p in input_paths}, key=str.casefold)
    if len(normalized) != len(input_paths):
        raise ValueError("--inputs 含重复路径，可能导致同一受访者被重复计数")
    process_dirs = []
    for value in normalized:
        path = Path(value)
        if "extracted" in path.parts:
            process_dirs.append(path.parents[len(path.parts) - path.parts.index("extracted") - 1])
    process_dir = process_dirs[0] if process_dirs and len({str(p) for p in process_dirs}) == 1 else None
    tier_by_source: dict[str, dict] = {}
    manifest_path = process_dir / "source-manifest.json" if process_dir else None
    if manifest_path and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tier_by_source = {str(item.get("source_id")): item for item in manifest.get("sources") or [] if isinstance(item, dict)}
    seen_source_ids: set[str] = set()
    for p in normalized:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"抽取文件不存在: {p}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data:
            raise ValueError(f"抽取文件必须是非空 JSON object: {path}")
        source_id = str(data.get("_source_id") or "").strip()
        if not re.fullmatch(r"P[0-9A-F]{8}", source_id):
            raise ValueError(f"抽取文件缺少稳定匿名 _source_id: {path}")
        if source_id in seen_source_ids:
            raise ValueError(f"多个抽取文件使用同一内容来源 {source_id}，禁止重复计数")
        seen_source_ids.add(source_id)
        source_rule = tier_by_source.get(source_id, {})
        extractions.append({
            "source": source_id,
            "source_file": data.get("_source_file", path.stem),
            "data": data,
            "evidence_tier": source_rule.get("evidence_tier", "primary"),
            "supplemented_fields": source_rule.get("supplemented_fields", []),
        })
    return extractions


def reduce_field(field_name: str, extractions: list) -> dict:
    """
    对单个字段做 reduce。
    返回: {"value": ..., "mention_count": N, "total": M, "mentioned_by": [...]}
          或对于列表字段: {"items": [{value, mention_count, mentioned_by}, ...]}
    """
    prompt_filename = FIELD_REDUCER_PROMPT.get(field_name, "reduce_generic.txt")

    prompt_template_path = PROMPTS_DIR / prompt_filename
    if not prompt_template_path.exists():
        raise FileNotFoundError(f"reducer prompt 不存在: {prompt_template_path}")

    if not SHARED_CONTRACT_PATH.exists():
        raise FileNotFoundError(f"共享语言契约不存在: {SHARED_CONTRACT_PATH}")
    prompt_template = (
        SHARED_CONTRACT_PATH.read_text(encoding="utf-8").strip()
        + "\n\n"
        + prompt_template_path.read_text(encoding="utf-8").strip()
    )

    # 从同一过程目录读取证据层级。补充材料只进入明确授权的字段，且不计主访谈频次。
    items = []
    for e in extractions:
        v = e["data"].get(field_name)
        if v is None:
            continue
        tier = e.get("evidence_tier", "primary")
        if tier == "supplemental" and field_name not in set(e.get("supplemented_fields") or []):
            continue
        items.append({
            "source": e["source"],
            "evidence_tier": tier,
            "value": v,
        })

    if not items:
        return None

    total = sum(1 for e in extractions if e.get("evidence_tier", "primary") == "primary")
    inputs_json = json.dumps(items, ensure_ascii=False, indent=2)

    full_prompt = (
        _PRIVACY_P0_BLOCK
        + "\n## 证据层级计数\nmention_count、mentioned_by 和分母只计算 primary。supplemental 可补充已授权字段的细节，不能增加频次，也不能单独形成核心结论。\n\n"
        + prompt_template
        .replace("{{FIELD_NAME}}", field_name)
        .replace("{{TOTAL}}", str(total))
        .replace("{{INPUTS}}", inputs_json)
    )

    logger.info(f"reduce {field_name}: {len(items)}/{total} 份提及")
    response = call_model(full_prompt)
    result = extract_json(response)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", required=True, help="要 reduce 的字段名")
    parser.add_argument("--inputs", nargs="+", required=True, help="抽取 JSON 路径列表")
    parser.add_argument("--output", required=True, help="reduce 结果输出路径")
    args = parser.parse_args()

    extractions = load_extractions(args.inputs)
    if not extractions:
        logger.error("没加载到任何抽取结果")
        sys.exit(1)

    result = reduce_field(args.field, extractions)
    if result is None:
        primary_total = sum(1 for item in extractions if item.get("evidence_tier", "primary") == "primary")
        result = {
            "field": args.field,
            "status": "not_mentioned",
            "value": None,
            "mention_count": 0,
            "total": primary_total,
            "mentioned_by": [],
            "evidence_quotes": [],
        }
        logger.warning(f"字段 '{args.field}' 在所有抽取中都不存在,写入明确缺失状态")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ reduce 完成: {output_path}")
    print(json.dumps({"success": True, "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
