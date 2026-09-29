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
        # 1. 获取目标用户的 user_id
        user_id = cl.user_id_from_username(TARGET)
        
        # 2. 直接发起 IG 原生 Private API 请求获取直播流，绕过 instagrapi 的方法变动
        mpd_url = None
        try:
            res = cl.private_request(f"live/user/{user_id}/")
            broadcast = res.get("broadcast") or {}
            mpd_url = broadcast.get("dash_playback_url") or broadcast.get("dash_abr_playback_url")
        except Exception:
            # 备用路径：通过 reels/story 接口二次确认
            try:
                res = cl.private_request("feed/reels_media/", params={"user_ids": user_id})
                reels = res.get("reels", {}).get(str(user_id), {})
                broadcast = reels.get("broadcast") or {}
                mpd_url = broadcast.get("dash_playback_url") or broadcast.get("dash_abr_playback_url")
            except Exception:
                pass

        if not mpd_url:
            print(f"[-] @{TARGET} 当前未开播（或未检测到推流地址）。")
            continue

        print(f"[+] 检测到 @{TARGET} 正在直播！成功提取推流地址，准备拉流录制...")

        filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        # 3. 使用 ffmpeg 录制推流地址
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
