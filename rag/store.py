"""知识卡加载与轻量检索（按模式过滤 + 关键词加权）。"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from rag.schema import card_to_text, normalize_mode, validate_card

ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = ROOT / "knowledge" / "cards"

TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_./—-]{2,}")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text or "")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    if not path.exists():
        return cards
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                card = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_no} JSON 无效: {exc}") from exc
            errors = validate_card(card)
            if errors:
                raise ValueError(f"{path.name}:{line_no} {'; '.join(errors)}")
            card["_text"] = card_to_text(card)
            card["_tokens"] = set(tokenize(card["_text"]))
            cards.append(card)
    return cards


@lru_cache(maxsize=1)
def load_all_cards() -> tuple[dict[str, Any], ...]:
    cards: list[dict[str, Any]] = []
    for name in ("elder.jsonl", "baby.jsonl", "pet.jsonl"):
        cards.extend(_iter_jsonl(CARDS_DIR / name))
    return tuple(cards)


def reload_cards() -> int:
    load_all_cards.cache_clear()
    return len(load_all_cards())


def score_card(card: dict[str, Any], query_tokens: set[str], scene: str | None) -> float:
    overlap = len(card["_tokens"] & query_tokens)
    score = float(overlap)

    # 场景加权
    if scene and scene in str(card.get("scene", "")):
        score += 3.0
    elif scene and scene != "其他" and str(card.get("scene")) == "其他":
        score += 0.5

    # 风险等级加权，高风险知识优先召回
    level = str(card.get("risk_level", ""))
    if level.startswith("高"):
        score += 1.2
    elif level.startswith("中"):
        score += 0.4

    # 来源完整度轻微加权
    if card.get("source_section"):
        score += 0.2
    return score


def retrieve_cards(
    mode: str,
    query: str = "",
    scene: str | None = None,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    mode_key = normalize_mode(mode)
    cards = [c for c in load_all_cards() if c.get("mode") == mode_key]
    if not cards:
        return []

    query_tokens = set(tokenize(query))
    # 无 query 时按场景 + 风险等级取一批默认卡
    if not query_tokens and scene:
        query_tokens = set(tokenize(scene))

    ranked = sorted(
        cards,
        key=lambda c: score_card(c, query_tokens, scene),
        reverse=True,
    )

    # 保证多场景覆盖：若 query 空，按场景轮询取样
    if not query.strip():
        picked: list[dict[str, Any]] = []
        seen_scenes: dict[str, int] = {}
        for card in ranked:
            sc = str(card.get("scene") or "其他")
            if seen_scenes.get(sc, 0) >= 2:
                continue
            picked.append(card)
            seen_scenes[sc] = seen_scenes.get(sc, 0) + 1
            if len(picked) >= top_k:
                break
        if picked:
            return picked

    return ranked[:top_k]


def format_cards_for_prompt(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""
    lines = ["# 参考知识卡（仅当画面可见对应情况时采用，不可臆造）"]
    for i, card in enumerate(cards, start=1):
        measures = card.get("measures") or []
        if isinstance(measures, str):
            measures = [measures]
        measure_text = "；".join(measures)
        lines.append(
            f"{i}. [{card.get('scene')}/{card.get('object')}] "
            f"属性:{card.get('attribute')}；风险:{card.get('risk')}（{card.get('risk_level')}）；"
            f"原则:{card.get('principle')}；措施:{measure_text}；"
            f"来源:{card.get('source')} · {card.get('source_section')}"
        )
    return "\n".join(lines)


def cards_as_public(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public = []
    for card in cards:
        public.append(
            {
                "id": card.get("id"),
                "mode": card.get("mode"),
                "scene": card.get("scene"),
                "crowd": card.get("crowd"),
                "object": card.get("object"),
                "attribute": card.get("attribute"),
                "risk": card.get("risk"),
                "risk_level": card.get("risk_level"),
                "principle": card.get("principle"),
                "measures": card.get("measures"),
                "source": card.get("source"),
                "source_section": card.get("source_section"),
                "tags": card.get("tags") or [],
            }
        )
    return public
