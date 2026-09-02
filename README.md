# Bot-Hosting Daily Coins

自动领取Bot-Hosting.net每日免费金币的GitHub Actions脚本

## 功能
- 每天UTC 9:00自动运行（北京时间17:00）
- 自动领取10个免费金币
- 支持手动触发
- 智能间隔避免rate limit

## 设置步骤
1. Fork或创建新仓库
2. 添加Secret: `BOT_HOSTING_TOKEN`
3. 启用Actions

## Token获取
1. 登录 https://legacy.bot-hosting.net/panel/
2. F12 → Console
3. 运行: `localStorage.getItem('token')`
4. 复制到GitHub Secrets
