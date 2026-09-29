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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在检测 @{TARGET} 是否开播...")

    try:
        user_id = cl.user_id_from_username(TARGET)
        print(f"[+] 获取到 @{TARGET} 的 UID: {user_id}")
        
        mpd_url = None
        broadcast_id = None

        # 通道 1: 模拟点击头像 (feed/user/{user_id}/story/)
        try:
            res_story = cl.private_request(f"feed/user/{user_id}/story/")
            broadcast = res_story.get("broadcast") or res_story.get("reel", {}).get("broadcast") or {}
            if broadcast:
                broadcast_id = broadcast.get("id")
                mpd_url = broadcast.get("dash_playback_url") or broadcast.get("dash_abr_playback_url")
        except Exception as e:
            print(f"[!] 通道 1 提示: {e}")

        # 通道 2: 主页详情接口 (users/{user_id}/info/)
        if not mpd_url and not broadcast_id:
            try:
                res_info = cl.private_request(f"users/{user_id}/info/")
                user_info = res_info.get("user", {})
                broadcast = user_info.get("broadcast") or {}
                broadcast_id = user_info.get("live_broadcast_id") or broadcast.get("id")
                if broadcast and not mpd_url:
                    mpd_url = broadcast.get("dash_playback_url") or broadcast.get("dash_abr_playback_url")
            except Exception as e:
                print(f"[!] 通道 2 提示: {e}")

        # 通道 3: 全局直播广播池 (feed/reels_tray/)
        if not mpd_url and not broadcast_id:
            try:
                res_tray = cl.private_request("feed/reels_tray/")
                broadcasts = res_tray.get("broadcasts", [])
                for b in broadcasts:
                    if str(b.get("user", {}).get("pk")) == str(user_id):
                        broadcast_id = b.get("id")
                        mpd_url = b.get("dash_playback_url") or b.get("dash_abr_playback_url")
                        break
            except Exception as e:
                print(f"[!] 通道 3 提示: {e}")

        # 如果拿到广播 ID 但缺失推流 URL，二次请求直播详情
        if broadcast_id and not mpd_url:
            try:
                print(f"[+] 识别到直播广播 ID: {broadcast_id}，正在提取 MPD 推流...")
                res_live = cl.private_request(f"live/{broadcast_id}/info/")
                mpd_url = res_live.get("dash_playback_url") or res_live.get("dash_abr_playback_url")
            except Exception as e:
                print(f"[!] 请求直播详情失败: {e}")

        if not mpd_url:
            print(f"[-] @{TARGET} 未能获取到有效的 MPD 推流地址。")
            continue

        print(f"[+] 成功抓取到直播推流！开始拉流录制...")
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
