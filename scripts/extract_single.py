"""
extract_single.py — 对单份预处理后的文本调模型,抽取画像 JSON

读 assets/prompts/extract_single.txt 和共享语言契约,把对齐字段集插入,
调当前环境配置的模型(由环境变量 ANTHROPIC_BASE_URL / ANTHROPIC_MODEL 决定)。

用法:
    python extract_single.py \\
        --input <workdir>/processed/<group>/<file>.txt \\
        --output <workdir>/extracted/<group>/<file>.json \\
        --fields '<对齐字段集 JSON>' \\
        --persona-type toB

环境变量:
    ANTHROPIC_BASE_URL      API endpoint(默认 https://api.anthropic.com)
    ANTHROPIC_AUTH_TOKEN    鉴权 token
    ANTHROPIC_MODEL         模型名(默认 claude-opus-4-5)
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests

logger = logging.getLogger("extract_single")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-opus-4-5"
DEFAULT_CHUNK_TOKENS = 12000  # 对弱模型保守，仍可通过参数或环境变量覆盖
CHARS_PER_TOKEN = 1.6  # 中文粗略估算

# Prompt 模板路径(相对于本文件)
PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "prompts" / "extract_single.txt"
SHARED_CONTRACT_PATH = Path(__file__).parent.parent / "assets" / "prompts" / "_shared-language-contract.txt"


def load_prompt_template() -> str:
    missing = [path for path in (SHARED_CONTRACT_PATH, PROMPT_TEMPLATE_PATH) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Prompt 模板不存在: {', '.join(str(path) for path in missing)}")
    return (
        SHARED_CONTRACT_PATH.read_text(encoding="utf-8").strip()
        + "\n\n"
        + PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    )


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数(中文按 1.6 字/token)"""
    return int(len(text) / CHARS_PER_TOKEN)


def split_long_document(text: str, max_tokens: int = DEFAULT_CHUNK_TOKENS) -> list:
    """长文档按对话轮次切分"""
    # 尝试按「时间戳-说话人-内容」格式切分
    # 常见格式:[00:01:23] 张三:xxx 或 张三:xxx 或 Q: xxx
    lines = text.split("\n")
    chunks = []
    current = []
    current_tokens = 0

    for line in lines:
        line_tokens = estimate_tokens(line)
        if line_tokens > max_tokens:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_tokens = 0
            max_chars = max(1, int(max_tokens * CHARS_PER_TOKEN))
            chunks.extend(line[start:start + max_chars] for start in range(0, len(line), max_chars))
            continue
        if current_tokens + line_tokens > max_tokens and current:
            chunks.append("\n".join(current))
            current = [line]
            current_tokens = line_tokens
        else:
            current.append(line)
            current_tokens += line_tokens

    if current:
        chunks.append("\n".join(current))

    return chunks


def stable_source_id(input_path: Path) -> str:
    """Create one stable anonymous ID per unique source content."""
    digest = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()[:8].upper()
    return f"P{digest}"


def call_model(prompt: str, document_text: str, max_retries: int = 1) -> dict:
    """调模型,返回解析后的 JSON dict"""
    base_url = os.environ.get("ANTHROPIC_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    if not auth_token:
        raise ValueError("环境变量 ANTHROPIC_AUTH_TOKEN 未设置")

    full_prompt = f"{prompt}\n\n## 访谈逐字稿\n\n{document_text}"

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
                    "max_tokens": 8192,
                    "messages": [{"role": "user", "content": full_prompt}],
                },
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]

            # 提取 JSON(模型可能在 ```json 代码块里返回)
            json_text = extract_json_from_response(content)
            return json.loads(json_text)

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            if attempt < max_retries:
                logger.warning(f"调用失败 (attempt {attempt+1}): {e},重试中...")
                time.sleep(2)
            else:
                raise


def extract_json_from_response(text: str) -> str:
    """从模型返回的文本里提取 JSON 部分"""
    # 优先匹配 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # 否则尝试找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise ValueError(f"无法从模型返回中提取 JSON: {text[:200]}")


def merge_chunked_results(results: list) -> dict:
    """Losslessly merge dynamic fields from chunk-level extraction results.

    Lists are concatenated, nested objects are merged recursively, and scalar
    disagreements are retained in _chunk_conflicts instead of being silently
    discarded. Downstream field reducers can then resolve those conflicts.
    """
    if not results:
        return {}
    if len(results) == 1:
        return results[0]

    merged: dict = {}
    conflicts: list[dict] = []

    def is_missing(value) -> bool:
        return value in (None, "", "文档未提及", "材料未提及", [], {})

    def merge_value(current, incoming, path: str):
        if is_missing(current):
            return incoming
        if is_missing(incoming) or current == incoming:
            return current
        if isinstance(current, list) and isinstance(incoming, list):
            return [*current, *incoming]
        if isinstance(current, dict) and isinstance(incoming, dict):
            out = dict(current)
            for key, value in incoming.items():
                child = f"{path}.{key}" if path else str(key)
                out[key] = merge_value(out.get(key), value, child)
            return out
        conflicts.append({"field": path, "values": [current, incoming]})
        return current

    for result in results:
        if not isinstance(result, dict):
            conflicts.append({"field": "$", "values": ["非对象分段结果", result]})
            continue
        for field, value in result.items():
            merged[field] = merge_value(merged.get(field), value, field)

    merged["_chunk_count"] = len(results)
    merged["_chunk_conflicts"] = conflicts
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="预处理后的 .txt 路径")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--fields", required=True, help="对齐字段集 JSON 字符串")
    parser.add_argument("--persona-type", default="toB", choices=["toB", "toC", "toD"])
    parser.add_argument(
        "--max-input-tokens",
        type=int,
        default=int(os.environ.get("PERSONA_MAX_INPUT_TOKENS", DEFAULT_CHUNK_TOKENS)),
        help="单个模型调用允许的访谈输入 token 粗估上限，弱模型默认 12000",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    fields = json.loads(args.fields)

    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_path}")
        sys.exit(1)

    document_text = input_path.read_text(encoding="utf-8")
    if not document_text.strip():
        logger.error(f"输入文件为空: {input_path}")
        sys.exit(1)

    # 加载 prompt 模板
    prompt_template = load_prompt_template()
    if isinstance(fields, dict):
        fields_desc = "\n".join(f"- `{key}`: {value}" for key, value in fields.items())
    elif isinstance(fields, list):
        fields_desc = "\n".join(f"- `{field}`" for field in fields)
    else:
        raise ValueError("--fields 必须是字段名数组或字段名到定义的 JSON 对象")
    source_id = stable_source_id(input_path)
    prompt = prompt_template.replace("{{FIELDS}}", fields_desc).replace("{{PERSONA_TYPE}}", args.persona_type).replace("{{SOURCE_FILE}}", source_id)

    # 检查是否需要分段
    token_count = estimate_tokens(document_text)
    if args.max_input_tokens < 1000:
        raise ValueError("--max-input-tokens 不能小于 1000")
    if token_count > args.max_input_tokens:
        logger.info(f"文档过长 ({token_count} tokens),分段处理")
        chunks = split_long_document(document_text, args.max_input_tokens)
        logger.info(f"切成 {len(chunks)} 段")
        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"处理第 {i+1}/{len(chunks)} 段")
            results.append(call_model(prompt, chunk))
        result = merge_chunked_results(results)
    else:
        result = call_model(prompt, document_text)

    # 添加来源标识
    result["_source_file"] = input_path.name
    result["_source_id"] = source_id

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ 抽取完成: {output_path}")
    print(json.dumps({"success": True, "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
