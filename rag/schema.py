"""知识卡字段约定。"""

from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = (
    "id",
    "mode",
    "scene",
    "crowd",
    "object",
    "attribute",
    "risk",
    "risk_level",
    "principle",
    "measures",
    "source",
    "source_section",
)

MODE_ALIASES = {
    "elder": "elder",
    "适老化": "elder",
    "baby": "baby",
    "育婴": "baby",
    "infant": "baby",
    "pet": "pet",
    "养宠": "pet",
}


def normalize_mode(mode: str) -> str:
    key = (mode or "elder").strip().lower()
    return MODE_ALIASES.get(key, "elder")


def card_to_text(card: dict[str, Any]) -> str:
    measures = card.get("measures") or []
    if isinstance(measures, str):
        measures = [measures]
    measure_text = "；".join(str(m) for m in measures if str(m).strip())
    return (
        f"场景:{card.get('scene','')} "
        f"人群:{card.get('crowd','')} "
        f"对象:{card.get('object','')} "
        f"属性:{card.get('attribute','')} "
        f"风险:{card.get('risk','')} "
        f"等级:{card.get('risk_level','')} "
        f"原则:{card.get('principle','')} "
        f"措施:{measure_text} "
        f"来源:{card.get('source','')} "
        f"章节:{card.get('source_section','')}"
    )


def validate_card(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in card or card[field] in (None, "", []):
            errors.append(f"缺少字段: {field}")
    if card.get("mode") not in {"elder", "baby", "pet"}:
        errors.append("mode 必须是 elder/baby/pet")
    if card.get("risk_level") not in {"高", "中", "低", "高风险", "中风险", "低风险"}:
        errors.append("risk_level 必须是 高/中/低")
    if not isinstance(card.get("measures"), list):
        errors.append("measures 必须是数组")
    return errors
