# Bot-Hosting.net 每日领金币

## 设置步骤

### 1. 创建GitHub仓库
1. 在GitHub创建一个新仓库（可以是私有的）
2. 克隆到本地

### 2. 添加Workflow文件
将 `.github/workflows/daily-coins.yml` 上传到仓库的 `.github/workflows/` 目录

### 3. 添加Secret
在仓库的 **Settings → Secrets and variables → Actions** 中添加：
- **名称**: `BOT_HOSTING_TOKEN`
- **值**: 你的Bot-Hosting token（就是那个eyJ开头的字符串）

### 4. 启用Workflow
GitHub会自动启用，也可以手动在Actions标签页启用

## 工作原理
- 每天UTC时间9点自动运行（北京时间17点）
- 检查今日是否已领满10个金币
- 如果没领满，自动逐个领取（每次间隔10秒）
- 支持手动触发

## Token获取方法
1. 登录 https://legacy.bot-hosting.net/panel/
2. 按F12打开开发者工具
3. 运行: `localStorage.getItem('token')`
4. 复制输出的token

## 注意事项
- 每天最多领10个免费金币
- 领取间隔10秒，避免触发rate limit
- Token泄露会导致账户被盗，务必设为Secret
