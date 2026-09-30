import os
import sys
import subprocess
from datetime import datetime

# 自动检查并安装 yt-dlp（用于从 MPD 流中自动锁死 720p/1080p 最高原画质）
try:
    import yt_dlp
except ImportError:
    print("[+] 正在自动安装 yt-dlp 以确保抓取高清画质...")
    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)

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

# 获取 instagrapi 正在使用的 Android App User-Agent，供 yt-dlp 伪装使用
ig_user_agent = getattr(cl, "user_agent", "Instagram 269.0.0.18.75 Android (33/13; 480dpi; 1080x2340; Xiaomi; M2012K11AC; vili; qcom; zh_CN; 383675034)")

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

        print(f"[+] 成功抓取到直播推流！正在检测画质清单并开始录制...")

        # 【新增诊断】打印当前推流地址中包含的所有可用画质轨道清单
        try:
            print("[+] --- yt-dlp 可用画质列表开始 ---")
            subprocess.run([
                "yt-dlp",
                "--user-agent", ig_user_agent,
                "-F",
                mpd_url
            ], check=False)
            print("[+] --- yt-dlp 可用画质列表结束 ---")
        except Exception as e:
            print(f"[!] 打印画质列表异常: {e}")
        
        # 保持保存为 .mp4 格式
        filename = f"{TARGET}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        # 正式下载命令
        cmd_record = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "-S", "res,br",                 # 强制按分辨率和码率最高排序，锁死原画
            "--user-agent", ig_user_agent,  # 伪装成 Instagram 客户端防止 403 拦截
            "--remux-video", "mp4",         # 强制调用 ffmpeg 整理文件头，确保 MP4 不损坏
            "--concurrent-fragments", "5",  # 5 线程多并发下载，防网络卡顿
            "--socket-timeout", "30",       # 30秒无数据传输判定为下播，自动正常结束保存
            "--retries", "10",              # 网络波动重试次数
            "--fragment-retries", "10",     # 分片获取失败重试次数
            "-o", filename,
            mpd_url
        ]

        subprocess.run(cmd_record, check=True)
        print(f"[SUCCESS] @{TARGET} 直播录制完毕，已保存为: {filename}")

    except Exception as e:
        print(f"[!] 处理 @{TARGET} 时发生错误: {e}")
