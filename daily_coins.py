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
    """使用浏览器领取一个金币：注入token → 打开页面 → NopeCHA 自动解题 → 点击确认按钮 → 检查结果"""
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    # 记录领取前的金币数
    headers = {"Authorization": token}
    resp_before = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
    coins_before = resp_before.json().get('coinsClaimed', 0) if resp_before.status_code == 200 else 0
    
    # 导航到领币页面（先注入 token 到 localStorage 实现网页认证）
    log("   📄 打开领币页面...")
    # 先打开域名根目录（避免直接访问 /panel/earn 被重定向到 /login）
    page.goto(f"{BOT_HOSTING_URL}/", wait_until="domcontentloaded", timeout=30000)
    # 注入 token 到 localStorage
    page.evaluate(f"""() => {{ localStorage.setItem('token', '{token}'); }}""")
    # 再导航到领币页面
    page.goto(f"{BOT_HOSTING_URL}/panel/earn", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    # 等待页面加载完成，检查是否有验证码
    page_text = page.locator("body").inner_text()
    has_captcha_btn = "Complete the captcha to claim coins!" in page_text
    
    if has_captcha_btn:
        log("   🔐 发现 'Complete the captcha to claim coins!' 按钮")
        log("   ⏳ 等待 NopeCHA 自动解题（最多 120 秒）...")
        
        # 等待 NopeCHA 自动填充验证码 token
        for i in range(120):
            time.sleep(1)
            solved = page.evaluate("""() => {
                const tas = document.querySelectorAll('textarea[name="h-captcha-response"], textarea[name="g-recaptcha-response"]');
                for (const ta of tas) {
                    if (ta.value && ta.value.trim().length > 20) return true;
                }
                return false;
            }""")
            if solved:
                log(f"   ✅ 验证码已自动解决（耗时 {i+1} 秒）")
                break
            if i % 10 == 0 and i > 0:
                log(f"   ⏳ 仍在等待解题... ({i} 秒)")
        else:
            log("   ⚠️  验证码解题超时(120s)", "WARN")
        
        time.sleep(1)
        
        # 点击 "Complete the captcha to claim coins!" 按钮
        try:
            btn = page.locator("button:has-text('Complete the captcha to claim coins!')").first
            if btn.is_visible(timeout=5000):
                btn.click()
                log("   ✅ 已点击确认按钮")
                time.sleep(3)
            else:
                log("   ⚠️  按钮不可见", "WARN")
        except Exception as e:
            log(f"   ⚠️  点击按钮失败: {e}", "WARN")
    else:
        # 没有 captcha 按钮，尝试直接找领取按钮
        log("   🔍 未发现 captcha 按钮，查找其他领取按钮...")
        try:
            btn = page.locator("button.btn-primary, button:has-text('Claim'), button:has-text('Earn')").first
            if btn.is_visible(timeout=5000):
                btn.click()
                log("   ✅ 已点击领取按钮")
                time.sleep(3)
        except Exception:
            pass
    
    # 检查领取结果：对比领取前后的 coinsClaimed 和总金币
    time.sleep(2)
    try:
        resp_after = requests.get(f"{API_URL}/freeCoinsStatus", headers=headers, timeout=10)
        if resp_after.status_code == 200:
            status_after = resp_after.json()
            coins_after = status_after.get('coinsClaimed', 0)
            
            resp_me = requests.get(f"{API_URL}/me", headers=headers, timeout=10)
            total_coins = resp_me.json().get('coins', 0) if resp_me.status_code == 200 else 0
            
            if coins_after > coins_before:
                return True, f"领取成功！coinsClaimed {coins_before}→{coins_after}, 总金币 {total_coins}"
            else:
                # 检查 claimable 是否变为 false（说明已领满或冷却）
                if not status_after.get('claimable', True):
                    return False, "服务器拒绝（claimable=false）"
                return False, f"金币未增加（{coins_before}→{coins_after}），可能需要重新解题"
    except Exception as e:
        log(f"   ⚠️  检查结果异常: {e}", "WARN")
    
    return False, "未能确认领取结果"


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
            headless=False,
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
        captcha_required = initial_status.get('captcha', False)
        
        log(f"📊 初始状态: coinsClaimed={initial_claimed}, claimable={claimable}, captcha={captcha_required}")
        
        # 只要 claimable=True 就尝试领取（coinsClaimed 可能是昨天的残留值）
        if not claimable:
            log("⏳ 冷却中，跳过")
            browser.close()
            return
        
        # 领取金币：最多尝试 10 次
        success_count = 0
        for i in range(1, 11):
            log(f"\n🎯 尝试第 {i} 个金币...")
            
            try:
                success, msg = claim_coin_with_browser(browser, token)
                if success:
                    log(f"✅ {msg}")
                    success_count += 1
                else:
                    log(f"❌ {msg}")
                    if "captcha" in msg.lower() or "Must solve" in msg:
                        log("   ⏹ 服务器要求验证码，停止重试")
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
