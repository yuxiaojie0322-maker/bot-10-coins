#!/usr/bin/env python3
"""
Bot-Hosting Daily Coins Claimer (Playwright + NopeCHA 扩展版)
流程：打开页面 → NopeCHA 自动解题 → 点击按钮 → 等待15秒 → 继续点击直到领满
在同一页面反复操作，不刷新页面（用户确认的操作节奏）
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
    print(f"[{t}] [{level}] {msg}", flush=True)


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


def get_coins(token):
    """获取总金币数"""
    try:
        resp = requests.get(f"{API_URL}/me", headers={"Authorization": token}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('coins', 0)
    except Exception:
        pass
    return -1


def get_status(token):
    """获取金币状态"""
    try:
        resp = requests.get(f"{API_URL}/freeCoinsStatus", headers={"Authorization": token}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def wait_captcha_solved(page, timeout=90):
    """等待 NopeCHA 自动解题完成，返回是否成功"""
    log("   🔐 等待 NopeCHA 自动解题...")
    for i in range(timeout):
        time.sleep(1)
        try:
            solved = page.evaluate("""() => {
                const tas = document.querySelectorAll('textarea[name="h-captcha-response"], textarea[name="g-recaptcha-response"]');
                for (const ta of tas) {
                    if (ta.value && ta.value.trim().length > 20) return true;
                }
                return false;
            }""")
        except Exception:
            solved = False
        if solved:
            log(f"   ✅ 验证码已自动解决（耗时 {i+1} 秒）")
            return True
        if i % 15 == 0 and i > 0:
            log(f"   ⏳ 仍在等待解题... ({i} 秒)")
    log(f"   ⚠️  验证码解题超时({timeout}s)", "WARN")
    return False


def click_claim_button(page):
    """点击页面上的领取按钮，返回是否点击成功及按钮文本"""
    try:
        clicked = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                if ((text.includes('Claim') || text.includes('claim') || 
                     text.includes('coin') || text.includes('Complete')) && !btn.disabled) {
                    btn.click();
                    return text;
                }
            }
            return null;
        }""")
        if clicked:
            log(f"   ✅ 已点击按钮: {clicked}")
            return True, clicked
        log("   ⚠️  未找到可点击的领取按钮", "WARN")
        return False, None
    except Exception as e:
        log(f"   ⚠️  点击失败: {e}", "WARN")
        return False, None


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
    
    # 初始状态
    status = get_status(token)
    initial_claimed = status.get('coinsClaimed', 0)
    claimable = status.get('claimable', False)
    coins_start = get_coins(token)
    log(f"📊 初始状态: coinsClaimed={initial_claimed}, claimable={claimable}, 总金币={coins_start}")
    
    if not claimable:
        log("⏳ 冷却中，跳过")
        return
    
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
        
        # 主页面：先打开域名根目录注入 token，再导航到领币页
        main_page = browser.pages[0] if browser.pages else browser.new_page()
        try:
            main_page.goto(f"{BOT_HOSTING_URL}/", wait_until="domcontentloaded", timeout=30000)
            main_page.evaluate(f"""() => {{ localStorage.setItem('token', '{token}'); }}""")
            log("✅ 网页认证已注入 (localStorage token)")
            main_page.goto(f"{BOT_HOSTING_URL}/panel/earn", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            log("✅ 已打开领币页面")
        except Exception as e:
            log(f"⚠️  打开页面失败: {e}", "WARN")
        
        # 领取金币：解题→点按钮→等15秒→继续点按钮
        success_count = 0
        max_attempts = 12  # 最多尝试 12 次
        
        for attempt in range(1, max_attempts + 1):
            # 检查是否已领满
            status = get_status(token)
            cur_claimed = status.get('coinsClaimed', 0)
            cur_coins = get_coins(token)
            
            log(f"\n🎯 第 {attempt} 次操作 | coinsClaimed={cur_claimed}, 总金币={cur_coins}")
            
            # 判断成功标准：总金币比开始多了 10 个则完成
            if cur_coins >= coins_start + 10:
                log(f"🎉 已领取 {cur_coins - coins_start} 个金币，任务完成！")
                break
            
            if not status.get('claimable', False):
                log("⏸ 服务器 claimable=false → 当日已领满 (You are on cooldown!)，退出")
                break
            
            # 检查页面是否有领取按钮
            page_text = main_page.locator("body").inner_text()
            has_btn = "Click here to claim one free coin!" in page_text or "Complete the captcha to claim coins!" in page_text
            
            if not has_btn:
                log("   📄 页面没有领取按钮，刷新页面...")
                try:
                    main_page.goto(f"{BOT_HOSTING_URL}/panel/earn", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                except Exception as e:
                    log(f"   ⚠️  刷新失败: {e}", "WARN")
                continue
            
            # 等待验证码解题（如果还没解）
            wait_captcha_solved(main_page, timeout=90)
            time.sleep(2)
            
            # 点击领取按钮
            clicked, btn_text = click_claim_button(main_page)
            if not clicked:
                # 点击失败，尝试刷新后重试
                log("   📄 点击失败，刷新页面重试...")
                try:
                    main_page.goto(f"{BOT_HOSTING_URL}/panel/earn", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                except Exception as e:
                    log(f"   ⚠️  刷新失败: {e}", "WARN")
                continue
            
            # 等待服务器处理（用户要求 15 秒）
            log("   ⏳ 等待 15 秒（服务器处理中）...")
            time.sleep(15)
            
            # 检查是否领取成功（总金币增加）
            new_coins = get_coins(token)
            if new_coins > coins_start:
                success_count = new_coins - coins_start
                log(f"   📈 当前已成功领取: {success_count}/10 (总金币 {new_coins})")
                # 领取成功，等待 15 秒后再继续（页面可能已刷新出新的验证码）
                time.sleep(15)
            else:
                log("   ⚠️  金币未增加，继续等待后重试")
        
        browser.close()
    
    # 最终统计
    log("\n" + "=" * 50)
    final_status = get_status(token)
    final_coins = get_coins(token)
    log(f"🪙 今日已领: {final_status.get('coinsClaimed', 0)}/10")
    log(f"💎 总硬币: {final_coins}")
    log(f"✅ 本次新增金币: {final_coins - coins_start} 个")
    log("=" * 50)


if __name__ == "__main__":
    main()
