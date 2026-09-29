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
        mpd_url = None
        
        # 1. 优先从 IG 现行的动态/故事流接口查询直播
        try:
            res = cl.private_request("feed/reels_media/", params={"user_ids": str(user_id)})
            reels = res.get("reels", {}) or res.get("reels_media", {})
            user_reel = reels.get(str(user_id), {}) if isinstance(reels, dict) else {}
            broadcast = user_reel.get("broadcast") or {}
            mpd_url = broadcast.get("dash_playback_url") or broadcast.get("dash_abr_playback_url")
        except Exception:
            pass

        # 2. 备用逻辑：从个人主页详情接口查询
        if not mpd_url:
            try:
                res_info = cl.private_request(f"users/{user_id}/info/")
                user_info = res_info.get("user", {})
                broadcast = user_info.get("broadcast") or {}
                mpd_url = broadcast.get("dash_playback_url") or broadcast.get("dash_abr_playback_url")
            except Exception:
                pass

        if not mpd_url:
            print(f"[-] @{TARGET} 当前未开播（未检测到有效直播推流）。")
            continue

        print(f"[+] 检测到 @{TARGET} 正在直播！成功提取推流地址，准备拉流录制...")

        filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        # 3. 调用 ffmpeg 录制
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
