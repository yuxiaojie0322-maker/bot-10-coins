#!/usr/bin/env python3
"""
Bot-Hosting.net 每日金币检查脚本
用法: python3 bot_hosting_check.py
"""

import json
import sys
import urllib.request
from pathlib import Path
from datetime import timedelta

CONFIG_FILE = Path.home() / ".bot_hosting_config.json"
API_BASE = "https://legacy.bot-hosting.net/api"

def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

def api_call(endpoint, token):
    """调用API，注意：不需要Bearer前缀"""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "message": f"HTTP {e.code}: {e.reason}", "code": e.code}
    except Exception as e:
        return {"error": True, "message": str(e)}

def main():
    config = load_config()
    
    if not config.get("token"):
        print("❌ 未登录，请先配置token")
        return 1
    
    token = config["token"]
    
    # 获取用户信息
    user = api_call("me", token)
    if user.get("error"):
        print(f"❌ 获取用户信息失败: {user.get('message')}")
        return 1
    
    # 获取金币状态
    status = api_call("freeCoinsStatus", token)
    if status.get("error"):
        print(f"❌ 获取金币状态失败: {status.get('message')}")
        return 1
    
    # 构建输出消息
    message = f"🪙 Bot-Hosting.net 每日金币检查\n"
    message += f"👤 用户: {user.get('username')}#{user.get('discriminator', '')}\n"
    message += f"💎 总硬币: {user.get('coins', 'N/A')}\n\n"
    
    if status.get("claimable"):
        message += "✅ 今天可以领取金币！\n"
        message += f"💰 已领取: {status.get('coinsClaimed', 0)}/10\n"
        message += "\n📋 请访问领取:\nhttps://legacy.bot-hosting.net/earn"
    elif status.get("timeLeft"):
        remaining = timedelta(seconds=status["timeLeft"])
        message += f"⏰ 冷却中，还需等待: {remaining}\n"
        message += f"💰 已领取: {status.get('coinsClaimed', 0)}/10"
    else:
        message += f"📊 今日状态: 已领取 {status.get('coinsClaimed', 0)}/10 金币"
    
    print(message)
    return 0

if __name__ == "__main__":
    sys.exit(main())
