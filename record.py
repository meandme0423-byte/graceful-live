import os
import sys
import subprocess
from datetime import datetime

# 自动检查并安装 yt-dlp
try:
    import yt_dlp
except ImportError:
    print("[+] 正在自动安装 yt-dlp...")
    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)

from instagrapi import Client

SESSION_ID = os.environ.get("IG_SESSION_ID", "").replace("sessionid=", "").strip()
TARGETS_RAW = os.environ.get("TARGET_USERNAME", "")

TARGETS = [t.strip().lstrip("@") for t in TARGETS_RAW.split(",") if t.strip()]

if not SESSION_ID or not TARGETS:
    print("[ERROR] 缺失 Secrets 配置！请检查 IG_SESSION_ID 和 TARGET_USERNAME。")
    sys.exit(1)

# 保留 instagrapi 仅用于验证账号登录状态是否有效
cl = Client()
try:
    cl.login_by_sessionid(SESSION_ID)
    print("[+] Instagram API 认证成功！")
except Exception as e:
    print(f"[!] SessionID 认证失败: {e}")
    sys.exit(1)

for TARGET in TARGETS:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在通过网页端通道检测 @{TARGET} 并录制最高画质...")

    try:
        filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        # 核心改变：直接指定 Instagram 网页端直播间地址
        web_live_url = f"https://www.instagram.com/{TARGET}/live/"

        # 核心改变：让 yt-dlp 模拟电脑端浏览器，并带上 Cookie 登录态直接抓取高清网页流
        cmd_record = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "-S", "res,br",                 # 锁死最高分辨率和最高码率
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # 伪装成桌面端 Chrome 浏览器
            "--add-header", f"Cookie: sessionid={SESSION_ID}",  # 注入你的登录 Cookie
            "--remux-video", "mp4",         # 自动封装为无损标准 mp4
            "--concurrent-fragments", "5",  # 多线程并发下载
            "--socket-timeout", "30",       # 30秒无数据判定为下播并自动收尾
            "--retries", "10",              
            "--fragment-retries", "10",     
            "-o", filename,
            web_live_url
        ]

        subprocess.run(cmd_record, check=True)
        print(f"[SUCCESS] @{TARGET} 直播录制完毕，已保存为: {filename}")

    except Exception as e:
        print(f"[!] 处理 @{TARGET} 时发生错误（若未开播属于正常跳过）: {e}")
