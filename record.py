import os
import sys
import datetime
import subprocess
from instagrapi import Client

def main():
    session_id = os.environ.get("SESSION_ID")
    target_username = os.environ.get("TARGET_USERNAME")

    if not session_id or not target_username:
        print("Error: Missing SESSION_ID or TARGET_USERNAME")
        sys.exit(1)

    print(f"Checking live status for @{target_username}...")

    cl = Client()
    try:
        cl.login_by_sessionid(session_id)
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    try:
        target_user_id = cl.user_id_from_username(target_username)
        broadcast = cl.user_live_broadcast(target_user_id)
    except Exception as e:
        print(f"Error checking live status: {e}")
        sys.exit(0)

    if not broadcast:
        print(f"User @{target_username} is not live.")
        sys.exit(0)

    print(f"User @{target_username} is currently live!")

    mpd_url = getattr(broadcast, 'dash_live_predictive_media_url', None) or getattr(broadcast, 'mpd_url', None)

    if not mpd_url:
        print("Failed to get MPD URL.")
        sys.exit(1)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{target_username}_{timestamp}.mp4"

    print(f"Recording to {filename}...")

    cmd_record = [
        "ffmpeg",
        "-y",
        "-rw_timeout", "30000000",   # 连续 30 秒收不到新数据自动退出并封包
        "-i", mpd_url,
        "-c", "copy",
        "-movflags", "+faststart",    # 补全 MP4 索引
        filename
    ]

    try:
        subprocess.run(cmd_record, check=True)
        print(f"Finished recording: {filename}")
    except subprocess.CalledProcessError as e:
        print(f"Recording stopped with code {e.returncode}")
    except Exception as e:
        print(f"Error during recording: {e}")

if __name__ == "__main__":
    main()
