#!/bin/bash
# Bot-Hosting.net 每日领金币检查脚本
# 由cron每天9点执行

CONFIG_FILE="$HOME/.bot_hosting_config.json"
SCRIPT_DIR="/run/csi/mount-root/nas/4079184d856ecc166ed19d4887083405/workspaces/default"

# 检查是否有token
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 未找到配置文件，请先运行登录"
    exit 1
fi

TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('token', ''))")

if [ -z "$TOKEN" ]; then
    echo "❌ Token为空，请重新登录"
    exit 1
fi

# 检查今日状态
echo "🪙 检查Bot-Hosting.net金币状态..."

STATUS=$(curl -s "https://legacy.bot-hosting.net/api/freeCoinsStatus" \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    --max-time 30)

# 解析状态
CLAIMABLE=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('claimable') else 'no')" 2>/dev/null || echo "no")
CLAIMED=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('coinsClaimed', 0))" 2>/dev/null || echo "0")
TIME_LEFT=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('timeLeft', 0))" 2>/dev/null || echo "0")

if [ "$CLAIMABLE" = "yes" ]; then
    echo "✅ 可以领取金币！已领取: $CLAIMED/10"
    echo "📋 请访问 https://legacy.bot-hosting.net/earn 手动领取"
elif [ "$TIME_LEFT" -gt 0 ] 2>/dev/null; then
    echo "⏰ 冷却中，还需等待 $TIME_LEFT 秒"
    echo "💰 已领取: $CLAIMED/10"
else
    echo "📊 今日状态: 已领取 $CLAIMED/10 金币"
fi
