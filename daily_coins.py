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


def claim_coin_with_browser(browser, token):
    """使用浏览器领取一个金币"""
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    # 导航到领币页面
    page.goto(f"{BOT_HOSTING_URL}/panel/earn", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    # 检查是否显示 "Complete the captcha to claim coins!"
    page_text = page.locator("body").inner_text()
    if "Complete the captcha to claim coins!" in page_text:
        log("   🔐 发现验证码确认按钮，等待 NopeCHA 自动解题...")
        # 等待 NopeCHA 自动填充（最多 60 秒）
        for i in range(60):
            time.sleep(1)
            # 检查验证码是否已解决
            solved = page.evaluate("""() => {
                const tas = document.querySelectorAll('textarea[name="h-captcha-response"], textarea[name="g-recaptcha-response"]');
                for (const ta of tas) {
                    if (ta.value && ta.value.trim().length > 20) return true;
                }
                return false;
            }""")
            if solved:
                log("   ✅ 验证码已自动解决")
                break
        else:
            log("   ⚠️  验证码解题超时", "WARN")
        
        # 查找并点击 "Complete the captcha to claim coins!" 按钮
        try:
            btn = page.locator("button:has-text('Complete the captcha to claim coins!'), button:has-text('Claim Coins'), button.btn-primary").first
            if btn.is_visible(timeout=5000):
                btn.click()
                time.sleep(3)
                log("   ✅ 已点击确认按钮")
            else:
                log("   ⚠️  未找到确认按钮", "WARN")
        except Exception as e:
            log(f"   ⚠️  点击按钮失败: {e}", "WARN")
    
    # 检查领取结果
    time.sleep(2)
    page_text = page.locator("body").inner_text()
    
    # 通过 API 验证是否成功
    headers = {"Authorization": token}
    resp = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
    if resp.status_code == 200:
        status = resp.json()
        coins_claimed = status.get('coinsClaimed', 0)
        if coins_claimed > 0:
            return True, f"成功领取 (已领 {coins_claimed}/10)"
    
    # 检查页面是否有成功消息
    if "success" in page_text.lower() or "claimed" in page_text.lower():
        return True, "领取成功"
    
    return False, page_text[:200] if page_text else "未知状态"


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
        
        # 获取初始状态
        headers = {"Authorization": token}
        resp = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ 获取状态失败: HTTP {resp.status_code}", "ERROR")
            browser.close()
            sys.exit(1)
        
        initial_status = resp.json()
        initial_claimed = initial_status.get('coinsClaimed', 0)
        claimable = initial_status.get('claimable', False)
        
        log(f"📊 初始状态: 已领 {initial_claimed}/10, claimable={claimable}")
        
        # 只要 claimable=True 就尝试领取（服务器可能允许领取新金币）
        if not claimable:
            log("⏳ 冷却中，跳过")
            browser.close()
            return
        
        # 领取金币
        success_count = 0
        for i in range(1, 11 - initial_claimed):
            log(f"\n🎯 尝试第 {i} 个金币...")
            
            try:
                success, msg = claim_coin_with_browser(browser, token)
                if success:
                    log(f"✅ {msg}")
                    success_count += 1
                else:
                    log(f"❌ {msg}")
                    break
            except Exception as e:
                log(f"⚠️  异常: {e}", "WARN")
                break
            
            time.sleep(3)
        
        browser.close()
    
    # 最终统计
    log("\n" + "=" * 50)
    try:
        final_resp = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
        if final_resp.status_code == 200:
            final_status = final_resp.json()
            log(f"🪙 今日已领: {final_status.get('coinsClaimed', 0)}/10")
        
        account_resp = requests.get(f"{API_URL}/me", headers=headers, timeout=10)
        if account_resp.status_code == 200:
            account = account_resp.json()
            log(f"💎 总硬币: {account.get('coins', 0)}")
    except Exception as e:
        log(f"⚠️  获取最终状态失败: {e}", "WARN")
    
    log(f"✅ 本次成功领取: {success_count} 个")
    log("=" * 50)


if __name__ == "__main__":
    main()
