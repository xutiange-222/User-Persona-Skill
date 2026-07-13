from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_confirmation_phrase_requires_md_delivery_first() -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    workflow = (ROOT / "steps" / "checkpoint-workflow.md").read_text(encoding="utf-8")
    checklist = (ROOT / "templates" / "checkpoints" / "CHECKPOINTS.md").read_text(encoding="utf-8")

    assert "先交付，后请求" in skill
    assert "禁止提前介绍下一检查点及其确认话术" in skill
    assert "当前检查点 MD 未生成、未落盘或尚未在本轮对话中交付时" in workflow
    assert "禁止预告下一检查点的确认短语" in workflow
    assert "当前节点 MD 未生成并交付给用户时" in checklist
