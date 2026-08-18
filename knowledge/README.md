# 家庭场景改造知识库（RAG 知识卡）

目标：不把标准 PDF 直接塞进模型，而是先蒸馏成可检索的**知识卡**。

## 目录结构

```
knowledge/cards/
  elder.jsonl   # 适老化（第一优先级）
  baby.jsonl    # 育婴（第二优先级）
  pet.jsonl     # 养宠（第三优先级）
rag/
  schema.py     # 字段约定
  store.py      # 加载 + 检索
```

## 知识卡字段

```json
{
  "id": "elder-living-furniture-corner-001",
  "mode": "elder",
  "scene": "客厅",
  "crowd": "老人",
  "object": "家具",
  "attribute": "尖锐边角",
  "risk": "碰撞磕伤",
  "risk_level": "高",
  "principle": "防磕碰",
  "measures": ["圆角处理", "加装防撞条"],
  "source": "《城市居家适老化改造指导手册》",
  "source_section": "家具与防撞",
  "tags": ["客厅", "防撞"]
}
```

## 来源优先级

1. 适老化：MZ/T 218—2024、《城市居家适老化改造指导手册》、《既有住宅适老化改造设计指南》
2. 育婴：《托育机构婴幼儿伤害预防指南（试行）》、GB/T 31179-2014
3. 养宠：GB/T 43839-2024、GB/T 45204-2025、犬猫饲养相关标准

> 当前种子卡是按上述标准/指南的常见要求蒸馏的结构化要点，便于 RAG；后续可用正式文本继续增补，不建议整本 PDF 原文入库。

## 校验

```bash
python scripts/validate_cards.py
```

## 检索 API

- `GET /api/knowledge/search?mode=elder&scene=卫生间&q=扶手&top_k=5`
- `POST /api/analyze` 会自动按模式检索知识卡，注入视觉模型提示词
