"""适老化居家安全评估后端：接收图片，调用视觉大模型返回 JSON 结果。"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

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

SYSTEM_PROMPT = """# Role
你是一位专业的适老化改造评估专家，熟悉中国《居家适老化改造规范》、老年人跌倒风险、防滑、防撞、无障碍设计、人因工程等知识。

# Task
根据用户拍摄的室内照片，识别画面中的环境风险，并为老年人提供专业、易理解、可执行的安全改造建议。

# Analysis Requirements
请重点分析以下内容：

1. 地面安全
- 地面是否湿滑
- 是否存在门槛、高低差
- 是否存在容易绊倒的地毯
- 是否有散落电线、杂物
- 是否存在容易滑倒的位置

2. 通行动线
- 是否有家具阻挡
- 通道是否足够宽
- 是否方便老人行走
- 是否适合轮椅或助行器通过（如适用）

3. 家具安全
- 是否存在尖锐边角
- 家具是否稳定
- 是否有容易碰撞的位置
- 是否建议增加扶手

4. 光照情况
- 是否存在照明不足
- 是否有逆光、阴影
- 夜间是否需要感应灯

5. 卫浴安全（若画面包含）
- 是否建议安装扶手
- 是否建议防滑垫
- 是否存在玻璃门风险
- 是否建议坐浴椅

6. 卧室安全（若画面包含）
- 床高度是否适宜
- 起夜路线是否安全
- 是否建议床边扶手
- 是否建议夜灯

7. 厨房安全（若画面包含）
- 是否存在高处取物风险
- 是否存在燃气隐患
- 是否存在热水烫伤风险

8. 其他风险
- 宠物用品
- 小台阶
- 电源插座位置
- 电线裸露
- 其他可能导致跌倒或受伤的问题

# Output Rules
只返回一个 JSON 对象，不要 markdown，不要额外说明。格式如下：
{
  "sceneLabel": "卫生间|卧室|客厅|厨房|走廊/玄关|其他",
  "score": 0到100的整数,
  "summary": "一句话概述整体风险",
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
- 如果无法判断，放入 unjudgable，并写明“图片无法判断：xxx”。
- 建议要简单、可执行、符合普通家庭预算。
- 优先指出影响老人跌倒、安全、行动便利的问题。
- 输出语言自然、易懂，避免过于专业的术语。
- risks 按风险从高到低排序，通常 2~5 条；每条 suggestions 1~3 条。
- score 越低表示越需要优先改造。"""

USER_PROMPT = (
    "请评估这张家居照片的适老化安全风险。"
    "严格按系统要求只返回 JSON，"
    "只依据画面可见信息，不要臆造。"
)

app = FastAPI(title="Age-friendly Home Analyzer")


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


def normalize_report(data: dict) -> dict:
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
                "benefit": benefit or "有助于降低老人跌倒或碰撞风险。",
            }
        )

    unjudgable = data.get("unjudgable") or data.get("无法判断") or []
    if isinstance(unjudgable, str):
        unjudgable = [unjudgable] if unjudgable.strip() else []
    clean_unjudgable = [str(x).strip() for x in unjudgable[:5] if str(x).strip()]

    try:
        score = int(data.get("score", 65))
    except (TypeError, ValueError):
        score = 65
    score = max(0, min(100, score))

    scene_label = str(data.get("sceneLabel") or data.get("scene") or "室内空间").strip()
    summary = str(data.get("summary") or "已完成适老化风险评估。").strip()

    if not clean_risks:
        clean_risks = [
            {
                "title": "存在潜在跌倒风险",
                "level": "中风险",
                "description": "画面中可能存在地面或通行方面的安全隐患。",
                "suggestions": ["检查地面防滑、通道通畅和必要扶手。"],
                "benefit": "可降低老人日常活动中的跌倒风险。",
            }
        ]

    # 兼容旧前端：汇总一条总建议列表
    upgrades = []
    for risk in clean_risks:
        upgrades.extend(risk["suggestions"][:1])
    upgrades = upgrades[:4]

    return {
        "sceneLabel": scene_label,
        "score": score,
        "summary": summary,
        "risks": clean_risks,
        "upgrades": upgrades,
        "unjudgable": clean_unjudgable,
        "model": VISION_MODEL,
    }


async def call_vision_model(image_b64: str, mime: str) -> dict:
    if not VISION_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="未配置 VISION_API_KEY。请复制 .env.example 为 .env 并填入密钥。",
        )

    payload = {
        "model": VISION_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
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

    return normalize_report(parsed)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "configured": bool(VISION_API_KEY),
        "model": VISION_MODEL,
        "baseUrl": VISION_BASE_URL,
    }


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="图片为空")
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片请小于 8MB")

    mime = image.content_type.split(";")[0].strip() or "image/jpeg"
    image_b64 = base64.b64encode(raw).decode("ascii")
    return await call_vision_model(image_b64, mime)


@app.get("/")
async def index():
    return FileResponse(ROOT / "index.html", media_type="text/html; charset=utf-8")


@app.get("/{filename}")
async def static_file(filename: str):
    if filename not in STATIC_FILES:
        raise HTTPException(status_code=404, detail="Not Found")
    path = ROOT / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path, media_type=STATIC_FILES[filename])


if __name__ == "__main__":
    import uvicorn

    if not VISION_API_KEY:
        print("警告：未检测到 VISION_API_KEY。请先配置 .env 后再进行识别。")
    print(f"打开 http://127.0.0.1:{PORT}")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)
