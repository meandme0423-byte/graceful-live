import os
import sys
import subprocess
from datetime import datetime
from instagrapi import Client

SESSION_ID = os.environ.get("IG_SESSION_ID", "").replace("sessionid=", "").strip()
TARGETS_RAW = os.environ.get("TARGET_USERNAME", "")

TARGETS = [t.strip().lstrip("@") for t in TARGETS_RAW.split(",") if t.strip()]

if not SESSION_ID or not TARGETS:
    print("[ERROR] 缺失 Secrets 配置！请检查 IG_SESSION_ID 和 TARGET_USERNAME。")
    sys.exit(1)

cl = Client()
try:
    cl.login_by_sessionid(SESSION_ID)
    print("[+] Instagram API 认证成功！")
except Exception as e:
    print(f"[!] SessionID 认证失败: {e}")
    sys.exit(1)

for TARGET in TARGETS:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在通过 API 检测 @{TARGET} 是否开播...")

    try:
        user_id = cl.user_id_from_username(TARGET)
        
        # 尝试通过 API 获取直播对象
        broadcast = None
        try:
            broadcast = cl.user_live_broadcast(user_id)
        except Exception as api_err:
            print(f"[!] 直播接口查询反馈: {api_err}")

        # 如果没有获取到 broadcast，打印提示
        if not broadcast or not getattr(broadcast, "dash_playback_url", None):
            print(f"[-] @{TARGET} 当前未检测到有效直播流。")
            continue

        mpd_url = broadcast.dash_playback_url
        print(f"[+] 检测到 @{TARGET} 正在直播！成功提取推流地址，准备拉流录制...")

        filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        cmd_record = [
            "ffmpeg",
            "-y",
            "-i", mpd_url,
            "-c", "copy",
            filename
        ]

        subprocess.run(cmd_record, check=True)
        print(f"[SUCCESS] @{TARGET} 直播录制完毕，已保存为: {filename}")

    except Exception as e:
        print(f"[!] 处理 @{TARGET} 时发生错误: {e}")
