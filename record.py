import os
import sys
import subprocess
from datetime import datetime

SESSION_ID = os.environ.get("IG_SESSION_ID", "")
TARGETS_RAW = os.environ.get("TARGET_USERNAME", "")

# 自动清洗用户名：去空格、去 @ 符号
TARGETS = [t.strip().lstrip("@") for t in TARGETS_RAW.split(",") if t.strip()]

if not SESSION_ID or not TARGETS:
    print("[ERROR] 缺失 Secrets 配置！请检查 IG_SESSION_ID 和 TARGET_USERNAME。")
    sys.exit(1)

# 清洗 session_id，防止用户误填 sessionid= 前缀
session_clean = SESSION_ID.replace("sessionid=", "").strip()

# 动态生成标准 Netscape 格式的 cookies.txt 文件
COOKIE_FILE = "cookies.txt"
cookie_content = (
    "# Netscape HTTP Cookie File\n"
    f".instagram.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\t{session_clean}\n"
)

with open(COOKIE_FILE, "w", encoding="utf-8") as f:
    f.write(cookie_content)

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

for TARGET in TARGETS:
    live_url = f"https://www.instagram.com/{TARGET}/live/"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在检查 @{TARGET} 是否开播...")

    # 1. 使用 --cookies 传入 cookie 文件进行检测
    cmd_check = [
        "yt-dlp",
        "--cookies", COOKIE_FILE,
        "--user-agent", user_agent,
        "-j",
        live_url
    ]

    result = subprocess.run(cmd_check, capture_output=True, text=True)

    if result.returncode != 0:
        stderr_msg = result.stderr.strip()
        if "is not live" in stderr_msg.lower() or "not currently live" in stderr_msg.lower():
            print(f"[-] @{TARGET} 当前未开播。")
        else:
            print(f"[!] 检测 @{TARGET} 提示信息:\n{stderr_msg}")
        continue

    # 2. 检测到开播，启动录制
    print(f"[+] 检测到 @{TARGET} 正在直播！准备拉流录制...")
    filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    cmd_record = [
        "yt-dlp",
        "--cookies", COOKIE_FILE,
        "--user-agent", user_agent,
        "-o", filename,
        "--concurrent-fragments", "5",
        live_url
    ]

    try:
        subprocess.run(cmd_record, check=True)
        print(f"[SUCCESS] @{TARGET} 直播录制完毕，已保存为: {filename}")
    except subprocess.CalledProcessError:
        print(f"[INFO] @{TARGET} 录制进程结束。")
