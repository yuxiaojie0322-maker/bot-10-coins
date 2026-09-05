# Bot-Hosting Daily Coins (Workflow 仓库)

> ⚠️ 本仓库**只包含 GitHub Actions workflow**，核心脚本已转移到 **Private 仓库 [bh-scripts](https://github.com/yuxiaojie0322-maker/bh-scripts)** 以保护 token 和业务逻辑。

## 用途

每天北京时间 09:00（UTC 01:00）自动领取 [Bot-Hosting.net](https://legacy.bot-hosting.net) 每日免费金币，并通过 Telegram 推送结果。

## 运行机制

| 步骤 | 内容 |
|------|------|
| 1 | Checkout 本仓库（workflow 本身） |
| 2 | Checkout Private 仓库 `bh-scripts`（拿 `daily_coins.py`） |
| 3 | 安装 Python + Playwright + xvfb |
| 4 | 下载 NopeCHA 扩展（用于自动解 hCaptcha） |
| 5 | 运行 `daily_coins.py` |
| 6 | TG 推送结果 |

## Secrets 配置

本仓库需要以下 Secrets（请在 Settings → Secrets and variables → Actions 中添加）：

| Secret 名 | 用途 |
|-----------|------|
| `BOT_HOSTING_TOKEN` | Bot-Hosting.net JWT token |
| `NOPECHA_KEY` | NopeCHA API key（用于 hCaptcha） |
| `TG_BOT_TOKEN` | Telegram Bot Token |
| `TG_CHAT_ID` | Telegram Chat ID |

> 💡 `GITHUB_TOKEN` 对同账号 Private 仓库有默认读取权限，无需额外 PAT。
