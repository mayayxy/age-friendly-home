# 长期公网分享

临时 `*.trycloudflare.com` 链接会在进程关闭后失效。要长期分享给互联网上的其他人，推荐以下两种方式。

## 方案 A：云部署（推荐，不依赖本机开机）

固定 HTTPS 地址，例如 `https://age-friendly-home.onrender.com`。

### Render 部署步骤

1. 将代码推送到 GitHub：`https://github.com/mayayxy/age-friendly-home`
2. 打开 [Render](https://render.com)，用 GitHub 登录
3. **New → Blueprint**，选择该仓库，Render 会读取根目录 `render.yaml`
4. 在部署界面填入环境变量 **VISION_API_KEY**（其余已在 yaml 中配置，可按需修改）
5. 部署完成后，Render 会给出固定 URL，可直接分享

说明：

- **Starter（$7/月）**：常驻在线，适合正式对外分享
- **Free**：15 分钟无访问会休眠，首次打开需等待约 30 秒唤醒

### 本地验证 Docker 镜像

```bash
docker build -t age-friendly-home .
docker run --rm -p 8000:8000 --env-file .env age-friendly-home
```

---

## 方案 B：Cloudflare 命名隧道 + 自有域名

适合继续在本机运行，但需要一个已接入 Cloudflare 的域名（如 `home.example.com`）。

### 一次性配置

```powershell
# 1. 登录 Cloudflare
cloudflared tunnel login

# 2. 创建隧道
cloudflared tunnel create age-friendly-home

# 3. 绑定 DNS（把 home 和 你的域名 换成实际值）
cloudflared tunnel route dns age-friendly-home home.你的域名.com

# 4. 编辑 deploy/cloudflare-tunnel.yml 中的 hostname 与 credentials-file 路径

# 5. 安装为 Windows 服务（开机自启）
cloudflared service install
cloudflared tunnel run age-friendly-home --config deploy/cloudflare-tunnel.yml
```

本机需保持 `python server.py` 运行；隧道服务负责把 HTTPS 流量转发到 `127.0.0.1:8000`。

---

## 对比

| 方式 | 固定链接 | 24/7 在线 | 成本 |
| --- | --- | --- | --- |
| trycloudflare 临时隧道 | 否 | 否（关终端即失效） | 免费 |
| Render Free | 是 | 休眠后需唤醒 | 免费 |
| Render Starter | 是 | 是 | ~$7/月 |
| Cloudflare 隧道 + 域名 | 是 | 本机开机时可用 | 域名费用 |

相机功能需要 **HTTPS**，以上方案均满足。
