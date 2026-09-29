name: IG Live Auto Recorder

on:
  schedule:
    # 设置每 5 分钟自动巡检一次开播状态
    - cron: '*/5 * * * *'
  workflow_dispatch: # 保留手动触发按钮，方便你随时点击测试

# 防冲突机制：当正在录制直播时，禁止新的定时巡检打断当前录制
concurrency:
  group: ig-live-recording
  cancel-in-progress: false

jobs:
  check-and-record:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg
          python -m pip install --upgrade pip
          pip install requests yt-dlp

      - name: Check and Record Stream
        env:
          IG_SESSION_ID: ${{ secrets.IG_SESSION_ID }}
          TARGET_USERNAME: ${{ secrets.TARGET_USERNAME }}
        run: |
          python record.py

      - name: Upload Video Artifact
        uses: actions/upload-artifact@v4
        if: always() # 只要脚本录到了视频，无论如何都打包上传
        with:
          name: ig-live-${{ github.run_id }}
          path: ./*.mp4
          retention-days: 7 # 自动保留 7 天（1周），过期后 GitHub 自动彻底清理
