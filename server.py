"""居家安全评估后端：接收图片与场景模式，调用视觉大模型返回 JSON 结果。"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from rag import cards_as_public, format_cards_for_prompt, reload_cards, retrieve_cards

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

VISION_API_KEY = os.getenv("VISION_API_KEY", "").strip()
VISION_BASE_URL = os.getenv(
    "VISION_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
).rstrip("/")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen-vl-plus").strip()
PORT = int(os.getenv("PORT", "8000"))

STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "app-web.js": "application/javascript; charset=utf-8",
}

JSON_OUTPUT_RULES = """
# Output Rules
只返回一个 JSON 对象，不要 markdown，不要额外说明。格式如下：
{
  "sceneLabel": "卫生间|卧室|客厅|厨房|走廊/玄关|其他",
  "score": 0到100的整数,
  "summary": "一句话概述；若无明显风险，写：相机范围内未识别到风险",
  "risks": [
    {
      "title": "风险短标题",
      "level": "高风险|中风险|低风险",
      "description": "一句话说明原因",
      "suggestions": ["可执行建议1", "可执行建议2"],
      "benefit": "说明能够降低哪些风险"
    }
  ],
  "unjudgable": ["图片无法判断的项目，没有则返回空数组"]
}

# Important Rules
- 只根据图片中能够观察到的信息分析。
- 不要猜测图片外的信息。
- 只报告确实存在、会影响安全的问题；不要为了凑条数而提示。
- 若相机范围内没有看到明确安全风险，risks 必须返回空数组 []，summary 写“相机范围内未识别到风险”。分数由系统根据风险等级计算，你无需纠结具体分数。
- 如果无法判断某项，放入 unjudgable；不要把“无法判断”写成风险。
- 建议要简单、可执行、符合普通家庭预算。
- 输出语言自然、易懂，避免生硬套话。
- 有风险时 risks 按从高到低排序，通常 1~4 条；每条 suggestions 1~3 条。
"""

MODE_PROMPTS = {
    "elder": {
        "label": "适老化",
        "default_benefit": "有助于降低老人跌倒或碰撞风险。",
        "fallback_summary": "相机范围内未识别到风险",
        "system": f"""# Role
你是一位专业的适老化改造评估专家，熟悉中国《居家适老化改造规范》、老年人跌倒风险、防滑、防撞、无障碍设计、人因工程等知识。

# Task
根据用户拍摄的室内照片，识别画面中的环境风险，并为老年人提供专业、易理解、可执行的安全改造建议。

# Analysis Requirements
请重点分析：地面安全、通行动线、家具安全、光照情况；若画面包含则分析卫浴/卧室/厨房安全；以及其他跌倒受伤风险。

优先指出影响老人跌倒、安全、行动便利的问题。没有明确风险时不要硬写建议。
{JSON_OUTPUT_RULES}""",
        "user": "请评估这张家居照片的适老化安全风险。严格按系统要求只返回 JSON，只依据画面可见信息，不要臆造。",
    },
    "baby": {
        "label": "婴儿安全",
        "default_benefit": "有助于降低婴幼儿磕碰、坠落或误触风险。",
        "fallback_summary": "相机范围内未识别到风险",
        "system": f"""# Role
你是一位专业的婴儿/幼儿居家安全装修评估专家，熟悉婴幼儿成长环境安全、防撞、防坠落、防误食误触、无毒环保装修等知识。

# Task
根据用户拍摄的室内照片，识别对婴幼儿（约 0-3 岁）不安全的装修与布置风险，并给出专业、易理解、可执行的改造建议。

# Analysis Requirements
请重点分析：防撞与家具安全、防坠落、地面与通行、电源与误触、误食与有害物、材料边角细节；厨房/卫浴仅在画面包含时分析。

优先指出会直接影响婴幼儿磕碰、坠落、误触、误食的问题。没有明确风险时不要硬写建议。
{JSON_OUTPUT_RULES}""",
        "user": "请评估这张家居照片的婴儿安全装修风险。严格按系统要求只返回 JSON，只依据画面可见信息，不要臆造。",
    },
    "pet": {
        "label": "宠物安全",
        "default_benefit": "有助于降低宠物受伤、误食或家庭连带损伤风险。",
        "fallback_summary": "相机范围内未识别到风险",
        "system": f"""# Role
你是一位专业的宠物友好装修与居家安全评估专家，熟悉猫狗等常见宠物的行为特点、防误食、防坠落、防滑、防卡困、以及宠物与人共居的空间安全知识。

# Task
根据用户拍摄的室内照片，识别对宠物不安全或容易引发破坏/连带伤害的装修与布置风险，并给出专业、易理解、可执行的改造建议。

# Analysis Requirements
请重点分析：误食与啃咬、滑倒与地面、坠落与开窗、卡困与夹伤、有毒/刺激物、休息与活动空间；其他共居风险仅在画面可见时指出。

优先指出会直接影响宠物误食、坠落、滑倒、卡困的问题。没有明确风险时不要硬写建议。
{JSON_OUTPUT_RULES}""",
        "user": "请评估这张家居照片的宠物安全装修风险。严格按系统要求只返回 JSON，只依据画面可见信息，不要臆造。",
    },
}

app = FastAPI(title="Home Safety Analyzer")


def get_mode_config(mode: str) -> dict:
    key = (mode or "elder").strip().lower()
    if key not in MODE_PROMPTS:
        key = "elder"
    return MODE_PROMPTS[key]


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_level(level: str) -> str:
    level = (level or "").strip()
    if level in {"高", "高风险", "high", "High"}:
        return "高风险"
    if level in {"低", "低风险", "low", "Low"}:
        return "低风险"
    return "中风险"


def normalize_suggestions(item: dict) -> list[str]:
    suggestions = item.get("suggestions")
    if isinstance(suggestions, list):
        return [str(x).strip() for x in suggestions[:3] if str(x).strip()]

    advice = item.get("advice") or item.get("改造建议")
    if isinstance(advice, list):
        return [str(x).strip() for x in advice[:3] if str(x).strip()]
    if isinstance(advice, str) and advice.strip():
        return [advice.strip()]
    return []


def score_from_risks(risks: list[dict]) -> int:
    """按风险等级计算分数。"""
    if not risks:
        return 100

    levels = [item.get("level") for item in risks]
    high = levels.count("高风险")
    mid = levels.count("中风险")
    low = levels.count("低风险")

    if high:
        return max(20, min(59, 52 - high * 8 - mid * 4 - low * 2))
    if mid:
        return max(60, min(79, 74 - mid * 5 - low * 2))
    return max(80, min(89, 88 - low * 3))


def status_from_score(score: int, has_risks: bool) -> str:
    if not has_risks or score >= 90:
        return ""
    if score < 60:
        return "优先改造"
    if score < 80:
        return "有风险"
    return "轻微风险"


def normalize_report(data: dict, mode: str = "elder") -> dict:
    cfg = get_mode_config(mode)
    risks = data.get("risks") or []
    clean_risks = []

    for item in risks[:5]:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title") or item.get("风险标题") or "").strip()
        description = str(
            item.get("description")
            or item.get("风险描述")
            or item.get("desc")
            or ""
        ).strip()
        benefit = str(item.get("benefit") or item.get("预期收益") or "").strip()
        level = normalize_level(str(item.get("level") or item.get("风险等级") or "中风险"))
        suggestions = normalize_suggestions(item)

        if not title and description:
            title = description[:18]
        if not description and title:
            description = title
        if not suggestions:
            continue

        clean_risks.append(
            {
                "title": title or "居家安全风险",
                "level": level,
                "description": description,
                "suggestions": suggestions,
                "benefit": benefit or cfg["default_benefit"],
            }
        )

    unjudgable = data.get("unjudgable") or data.get("无法判断") or []
    if isinstance(unjudgable, str):
        unjudgable = [unjudgable] if unjudgable.strip() else []
    clean_unjudgable = [str(x).strip() for x in unjudgable[:5] if str(x).strip()]

    score = score_from_risks(clean_risks)
    status = status_from_score(score, bool(clean_risks))

    scene_label = str(data.get("sceneLabel") or data.get("scene") or "室内空间").strip()
    summary = str(data.get("summary") or "").strip()

    if not clean_risks:
        summary = "相机范围内未识别到风险"
    elif not summary:
        summary = cfg["fallback_summary"]

    upgrades = []
    for risk in clean_risks:
        upgrades.extend(risk["suggestions"][:1])
    upgrades = upgrades[:4]

    return {
        "mode": cfg["label"],
        "modeKey": mode if mode in MODE_PROMPTS else "elder",
        "sceneLabel": scene_label,
        "score": score,
        "status": status,
        "summary": summary,
        "risks": clean_risks,
        "upgrades": upgrades,
        "unjudgable": clean_unjudgable,
        "model": VISION_MODEL,
        "knowledgeRefs": [],
    }


MODE_RETRIEVAL_QUERY = {
    "elder": "跌倒 防滑 扶手 通道 照明 门槛 碰撞 起夜",
    "baby": "防撞 坠落 误食 插座 门栏 烫伤 缠绕 倾倒",
    "pet": "误食 电线 坠落 防滑 卡困 逃逸 清洁剂 纱窗",
}


async def call_vision_model(image_b64: str, mime: str, mode: str = "elder") -> dict:
    if not VISION_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="未配置 VISION_API_KEY。请复制 .env.example 为 .env 并填入密钥。",
        )

    cfg = get_mode_config(mode)
    cards = retrieve_cards(
        mode=mode,
        query=MODE_RETRIEVAL_QUERY.get(mode, ""),
        top_k=8,
    )
    knowledge_block = format_cards_for_prompt(cards)
    system_prompt = cfg["system"]
    if knowledge_block:
        system_prompt = f"{cfg['system']}\n\n{knowledge_block}"

    payload = {
        "model": VISION_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": cfg["user"]},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                    },
                ],
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {VISION_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{VISION_BASE_URL}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"调用模型失败：{exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"模型接口错误（{response.status_code}）：{response.text[:500]}",
        )

    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"模型返回格式异常：{body}") from exc

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )

    try:
        parsed = extract_json(str(content))
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"无法解析模型 JSON：{str(content)[:400]}"
        ) from exc

    report = normalize_report(parsed, mode)
    report["knowledgeRefs"] = [
        {
            "id": c.get("id"),
            "source": c.get("source"),
            "source_section": c.get("source_section"),
            "scene": c.get("scene"),
            "risk": c.get("risk"),
        }
        for c in cards
    ]
    return report


@app.get("/api/health")
async def health():
    try:
        card_count = reload_cards()
        rag_ok = True
        rag_error = ""
    except Exception as exc:
        card_count = 0
        rag_ok = False
        rag_error = str(exc)

    return {
        "ok": True,
        "configured": bool(VISION_API_KEY),
        "model": VISION_MODEL,
        "baseUrl": VISION_BASE_URL,
        "modes": list(MODE_PROMPTS.keys()),
        "rag": {"ok": rag_ok, "cards": card_count, "error": rag_error},
    }


@app.get("/api/knowledge/search")
async def knowledge_search(
    mode: str = Query("elder"),
    scene: str = Query(""),
    q: str = Query(""),
    top_k: int = Query(8, ge=1, le=20),
):
    cards = retrieve_cards(mode=mode, query=q, scene=scene or None, top_k=top_k)
    return {
        "mode": mode,
        "scene": scene,
        "query": q,
        "count": len(cards),
        "items": cards_as_public(cards),
    }


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    mode: str = Form("elder"),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="图片为空")
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片请小于 8MB")

    mode_key = (mode or "elder").strip().lower()
    if mode_key not in MODE_PROMPTS:
        mode_key = "elder"

    mime = image.content_type.split(";")[0].strip() or "image/jpeg"
    image_b64 = base64.b64encode(raw).decode("ascii")
    return await call_vision_model(image_b64, mime, mode_key)


def file_response(path: Path, media_type: str) -> FileResponse:
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/")
async def index():
    return file_response(ROOT / "index.html", "text/html; charset=utf-8")


@app.get("/{filename}")
async def static_file(filename: str):
    if filename not in STATIC_FILES:
        raise HTTPException(status_code=404, detail="Not Found")
    path = ROOT / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    return file_response(path, STATIC_FILES[filename])


if __name__ == "__main__":
    import uvicorn

    if not VISION_API_KEY:
        print("警告：未检测到 VISION_API_KEY。请先配置 .env 后再进行识别。")
    print(f"打开 http://127.0.0.1:{PORT}")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)
