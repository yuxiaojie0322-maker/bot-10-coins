#!/usr/bin/env python3
"""
Bot-Hosting Daily Coins Claimer (Playwright + NopeCHA 扩展版)
使用浏览器自动化 + NopeCHA 扩展自动解题，支持免费计划
"""

import os
import sys
import time
import requests

BOT_HOSTING_URL = "https://legacy.bot-hosting.net"
API_URL = f"{BOT_HOSTING_URL}/api"
NOPECHA_KEY = os.environ.get("NOPECHA_KEY", "").strip()
EXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "scripts", "extensions", "nopecha", "unpacked")


def log(msg, level="INFO"):
    from datetime import datetime
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] [{level}] {msg}")


def get_token():
    """获取 Bot-Hosting token"""
    token = os.environ.get("BOT_HOSTING_TOKEN", "").strip()
    if token:
        return token
    config_path = os.path.expanduser("~/.bot_hosting_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            import json
            config = json.load(f)
            return config.get("token", "").strip()
    return ""


def claim_coin_with_browser(browser, token, captcha_token=None):
    """使用浏览器领取一个金币"""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    
    # 先获取状态
    resp = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    
    status = resp.json()
    coins_claimed = status.get('coinsClaimed', 0)
    claimable = status.get('claimable', False)
    
    if coins_claimed >= 10:
        return True, "今日已领满"
    if not claimable:
        return False, "冷却中"
    
    # 用浏览器操作
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    # 导航到领币页面
    page.goto(f"{BOT_HOSTING_URL}/panel/earn", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    
    # 检查是否有验证码
    has_captcha = page.evaluate("""() => {
        const tas = document.querySelectorAll('textarea[name="h-captcha-response"], textarea[name="g-recaptcha-response"]');
        for (const ta of tas) {
            if (ta.value && ta.value.trim().length > 20) return true;
        }
        return false;
    }""")
    
    if not has_captcha and captcha_token:
        # 注入 captcha token
        page.evaluate(f"""() => {{
            const tas = document.querySelectorAll('textarea[name="h-captcha-response"], textarea[name="g-recaptcha-response"]');
            tas.forEach(ta => {{ ta.value = '{captcha_token}'; ta.dispatchEvent(new Event('input', {{bubbles: true}})); }});
        }}""")
        time.sleep(1)
    
    # 点击领取按钮
    button = page.locator("button:has-text('Claim'), button:has-text('领取'), button.btn-primary").first
    if button.is_visible(timeout=5000):
        button.click()
        time.sleep(3)
        
        # 检查是否成功
        success_text = page.locator("body").inner_text()
        if "success" in success_text.lower() or "claimed" in success_text.lower() or "恭喜" in success_text:
            return True, "领取成功"
        elif "captcha" in success_text.lower() or "verify" in success_text.lower():
            return False, "需要验证码"
        else:
            # 再次检查状态
            resp2 = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
            new_claimed = resp2.json().get('coinsClaimed', 0)
            if new_claimed > coins_claimed:
                return True, f"领取成功 (已领 {new_claimed}/10)"
            return False, "未知状态"
    else:
        return False, "未找到领取按钮"


def main():
    log("=" * 50)
    log("🪙 Bot-Hosting 每日领金币 (NopeCHA 扩展版)")
    log("=" * 50)
    
    # 获取 token
    token = get_token()
    if not token:
        log("❌ 未找到 BOT_HOSTING_TOKEN", "ERROR")
        sys.exit(1)
    log("✅ Token 已加载")
    
    # 检查 NopeCHA key
    if not NOPECHA_KEY:
        log("⚠️  未配置 NOPECHA_KEY，无法解验证码", "WARN")
    
    # 启动浏览器
    from playwright.sync_api import sync_playwright
    
    ext_ok = os.path.exists(EXT_PATH) and os.path.exists(os.path.join(EXT_PATH, "manifest.json"))
    log(f"✅ NopeCHA 扩展 {'已加载' if ext_ok else '未找到'}")
    
    launch_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
    ]
    if ext_ok:
        launch_args.extend([
            f"--disable-extensions-except={EXT_PATH}",
            f"--load-extension={EXT_PATH}",
        ])
    
    with sync_playwright() as p:
        user_data_dir = "/tmp/playwright-bot-hosting"
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            args=launch_args,
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1440, "height": 900},
        )
        
        # 激活 NopeCHA
        if ext_ok and NOPECHA_KEY:
            try:
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(f"https://nopecha.com/setup#{NOPECHA_KEY}", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                log("✅ NopeCHA 已激活")
            except Exception as e:
                log(f"⚠️  NopeCHA 激活失败: {e}", "WARN")
        
        # 领取金币
        success_count = 0
        captcha_token = None
        
        for i in range(1, 11):
            # 检查状态
            headers = {"Authorization": token}
            try:
                resp = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
                status = resp.json()
                coins_claimed = status.get('coinsClaimed', 0)
                claimable = status.get('claimable', False)
                
                if coins_claimed >= 10:
                    log(f"📊 今日已领满: {coins_claimed}/10")
                    break
                if not claimable:
                    log(f"⏳ 冷却中，跳过")
                    break
                
                log(f"📊 尝试第 {i} 个金币 (已领: {coins_claimed}/10)...")
                
                success, msg = claim_coin_with_browser(browser, token, captcha_token)
                if success:
                    log(f"✅ {msg}")
                    success_count += 1
                    captcha_token = None  # 重置 captcha token
                else:
                    log(f"❌ {msg}")
                    if "captcha" in msg.lower() and not captcha_token and ext_ok:
                        log("🔐 等待 NopeCHA 自动解题...")
                        time.sleep(5)
                        # 重试
                        success, msg = claim_coin_with_browser(browser, token, captcha_token)
                        if success:
                            log(f"✅ 验证码已解，领取成功: {msg}")
                            success_count += 1
            except Exception as e:
                log(f"⚠️  请求失败: {e}", "WARN")
            
            time.sleep(3)
        
        browser.close()
    
    # 最终统计
    log("\n" + "=" * 50)
    headers = {"Authorization": token}
    try:
        final_status = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10).json()
        log(f"🪙 今日已领: {final_status.get('coinsClaimed', 0)}/10")
        
        account = requests.get(f"{API_URL}/me", headers=headers, timeout=10).json()
        log(f"💎 总硬币: {account.get('coins', 0)}")
    except:
        pass
    log(f"✅ 本次成功领取: {success_count} 个")
    log("=" * 50)


if __name__ == "__main__":
    main()
