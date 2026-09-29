import os
import sys
import subprocess
from datetime import datetime

SESSION_ID = os.environ.get("IG_SESSION_ID")
TARGETS_RAW = os.environ.get("TARGET_USERNAME", "")

# 自动按逗号拆分多个账号，并剔除首尾空格
TARGETS = [t.strip() for t in TARGETS_RAW.split(",") if t.strip()]

if not SESSION_ID or not TARGETS:
    print("[ERROR] 缺失 Secrets 配置！请检查 IG_SESSION_ID 和 TARGET_USERNAME。")
    sys.exit(1)

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 循环检查列表里的每一个账号
for TARGET in TARGETS:
    live_url = f"https://www.instagram.com/{TARGET}/live/"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在检查 @{TARGET} 是否开播...")

    # 1. 使用 yt-dlp 检测开播状态
    cmd_check = [
        "yt-dlp",
        "--add-header", f"Cookie:sessionid={SESSION_ID}",
        "--add-header", f"User-Agent:{user_agent}",
        "-j",
        live_url
    ]

    result = subprocess.run(cmd_check, capture_output=True, text=True)

    # 未开播时跳过，继续检查下一个
    if result.returncode != 0 or "is not live" in result.stderr.lower():
        print(f"[-] @{TARGET} 当前未开播。")
        continue

    # 2. 检测到开播，启动拉流录制
    print(f"[+] 检测到 @{TARGET} 正在直播！准备拉流录制...")
    filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    cmd_record = [
        "yt-dlp",
        "--add-header", f"Cookie:sessionid={SESSION_ID}",
        "--add-header", f"User-Agent:{user_agent}",
        "-o", filename,
        "--concurrent-fragments", "5",
        live_url
    ]

    try:
        subprocess.run(cmd_record, check=True)
        print(f"[SUCCESS] @{TARGET} 直播录制完毕，已保存为: {filename}")
    except subprocess.CalledProcessError:
        print(f"[INFO] @{TARGET} 录制进程结束（主播关播或连接中断）。")
