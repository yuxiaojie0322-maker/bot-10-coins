#!/usr/bin/env python3
"""
Bot-Hosting Daily Coins Claimer - Simple Version
"""

import requests
import json
import time
import os
import sys

BOT_HOSTING_URL = "https://legacy.bot-hosting.net/api"

def get_token():
    """Get Bot-Hosting token"""
    token = os.environ.get("BOT_HOSTING_TOKEN")
    if token:
        return token
    
    config_path = os.path.expanduser("~/.bot_hosting_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get("token")
    
    raise ValueError("Token not found")

def main():
    print("=" * 50)
    print("🪙 Bot-Hosting Daily Coins Claimer")
    print("=" * 50)
    
    # Get token
    try:
        token = get_token()
        print("✅ Token loaded")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    headers = {"Authorization": token}
    
    # Get status
    status = requests.get(f"{BOT_HOSTING_URL}/freeCoinsStatus", headers=headers, timeout=10).json()
    coins_claimed = status.get('coinsClaimed', 0)
    claimable = status.get('claimable', False)
    captcha_required = status.get('captcha', False)
    
    print(f"\n📊 今日已领: {coins_claimed}/10")
    print(f"⏰ 可领取: {claimable}")
    print(f"🔒 验证码: {captcha_required}")
    
    if coins_claimed >= 10:
        print("\n✅ 今日金币已领满!")
        return
    
    if not claimable:
        print("\n⏳ 冷却中，跳过...")
        return
    
    # Claim coins
    print(f"\n🎯 开始领取...")
    success_count = 0
    
    for i in range(1, 11 - coins_claimed):
        print(f"\n   尝试 {i}/{10-coins_claimed}...", end=" ")
        
        resp = requests.post(f"{BOT_HOSTING_URL}/freeCoins", 
                            headers=headers, 
                            json={}, 
                            timeout=30)
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("success"):
                print(f"✅ {result.get('message', 'Success')}")
                success_count += 1
            else:
                print(f"❌ {result.get('message', 'Unknown')}")
        else:
            print(f"❌ HTTP {resp.status_code}")
        
        time.sleep(3)
    
    # Final status
    print("\n" + "=" * 50)
    final_status = requests.get(f"{BOT_HOSTING_URL}/freeCoinsStatus", headers=headers, timeout=10).json()
    print(f"🪙 今日已领: {final_status.get('coinsClaimed', 0)}/10")
    
    account = requests.get(f"{BOT_HOSTING_URL}/me", headers=headers, timeout=10).json()
    print(f"💎 总硬币: {account.get('coins', 0)}")
    print(f"✅ 成功领取: {success_count} 个")
    print("=" * 50)

if __name__ == "__main__":
    main()
