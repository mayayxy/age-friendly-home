# 安居适老助手（网页版）

帮助有老人的家庭快速发现居家安全隐患，并给出适老化改造建议。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置视觉模型密钥

复制环境变量模板：

```bash
copy .env.example .env
```

编辑 `.env`，填入你的 API Key。默认使用阿里云通义千问视觉模型：

```env
VISION_API_KEY=你的密钥
VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen-vl-plus
PORT=8000
```

也可换成其他 OpenAI 兼容视觉接口，例如：

| 服务商 | BASE_URL | MODEL 示例 |
| --- | --- | --- |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2-VL-72B-Instruct` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |

通义密钥可在 [DashScope 控制台](https://dashscope.console.aliyun.com/) 创建。

### 3. 启动

```bash
python server.py
```

或双击 `start.bat`。

然后用手机或电脑打开：

[http://127.0.0.1:8000](http://127.0.0.1:8000)

同一局域网下，手机可访问电脑的局域网 IP，例如 `http://192.168.x.x:8000`。

## 当前能力

- 打开页面即启用实时相机
- 对准空间并识别（适老化 / 婴儿安全 / 宠物安全）
- 基于家庭场景改造知识卡做 RAG 检索增强
- 结果以底部弹层展示风险和改造建议

## RAG 知识库

标准不直接塞 PDF，而是蒸馏成知识卡，目录见 `knowledge/`。

```bash
python scripts/validate_cards.py
```

检索示例：

```text
GET /api/knowledge/search?mode=elder&scene=卫生间&q=扶手
```

## 长期分享给互联网用户

临时 `trycloudflare.com` 链接会过期。要固定、可长期分享的 HTTPS 地址，见 **[deploy/README.md](deploy/README.md)**：

- **推荐**：部署到 Render（固定 URL，不依赖本机开机）
- **备选**：Cloudflare 命名隧道 + 自有域名（本机常驻运行）

## 说明

请通过本地服务打开页面以使用相机（`http://127.0.0.1:8000`）。手机访问时请使用电脑局域网 IP，并允许浏览器相机权限。
