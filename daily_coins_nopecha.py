#!/usr/bin/env python3
"""Bot-Hosting Daily Coins Claimer with NopeCHA"""
import requests, json, time, os, sys

BOT_HOSTING_URL = "https://legacy.bot-hosting.net/api"
NOPECHA_API_URL = "https://api.nopecha.com/hcaptcha"
NOPECHA_KEY = os.environ.get("NOPECHA_KEY", "qifr6gi669wcvuj8iy30rq2j410wfjwm")

def get_token():
    token = os.environ.get("BOT_HOSTING_TOKEN")
    if token: return token
    config_path = os.path.expanduser("~/.bot_hosting_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get("token")
    raise ValueError("Token not found")

def solve_captcha(site_key, page_url, api_key=None):
    key = api_key or NOPECHA_KEY
    try:
        resp = requests.post(NOPECHA_API_URL, json={"key": key, "sitekey": site_key, "url": page_url}, timeout=30)
        if resp.status_code != 200:
            print(f"❌ NopeCHA error: {resp.status_code}")
            return None
        data = resp.json()
        task_id = data.get("id")
        if not task_id:
            print(f"❌ No task ID: {data}")
            return None
        print(f"⏳ Solving captcha... (task: {task_id})")
        for _ in range(60):
            time.sleep(2)
            result = requests.get(f"{NOPECHA_API_URL}/{task_id}", timeout=10).json()
            if result.get("solution"):
                token = result["solution"].get("token")
                if token:
                    print(f"✅ Captcha solved!")
                    return token
            if result.get("error"):
                print(f"❌ NopeCHA error: {result['error']}")
                return None
        print("⏰ Timeout")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("=" * 50)
    print("🪙 Bot-Hosting Daily Coins Claimer")
    print("🤖 With NopeCHA")
    print("=" * 50)
    
    try:
        token = get_token()
        print("✅ Token loaded")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Get status
    headers = {"Authorization": token}
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
    
    # Solve captcha
    captcha_token = None
    if captcha_required:
        print("\n🔐 求解验证码...")
        captcha_token = solve_captcha("10000000-FFFF-FFFF-FFFF-000000000001", "https://legacy.bot-hosting.net/panel/earn")
        if not captcha_token:
            print("\n❌ 验证码求解失败")
            return
    
    # Claim coins
    print(f"\n🎯 开始领取...")
    success_count = 0
    
    for i in range(1, 11 - coins_claimed):
        print(f"\n   尝试 {i}/{10-coins_claimed}...", end=" ")
        
        headers = {"Authorization": token, "Content-Type": "application/json"}
        data = {}
        if captcha_token:
            data["gRecaptchaResponse"] = captcha_token
        
        resp = requests.post(f"{BOT_HOSTING_URL}/freeCoins", headers=headers, json=data, timeout=30)
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("success"):
                print(f"✅ {result.get('message', 'Success')}")
                success_count += 1
            else:
                print(f"❌ {result.get('message', 'Unknown')}")
        else:
            print(f"❌ HTTP {resp.status_code}")
        
        time.sleep(10)
    
    # Final status
    print("\n" + "=" * 50)
    final_status = requests.get(f"{BOT_HOSTING_URL}/freeCoinsStatus", headers=headers, timeout=10).json()
    print(f"🪙 今日已领: {final_status.get('coinsClaimed', 0)}/10")
    
    account = requests.get(f"{BOT_HOSTING_URL}/me", headers=headers, timeout=10).json()
    print(f"💎 总硬币: {account.get('coins', 0)}")
    print(f"✅ 成功领取 {success_count} 个金币!")
    print("=" * 50)

if __name__ == "__main__":
    main()
