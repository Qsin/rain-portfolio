#!/usr/bin/env bash
# 视频压缩脚本（带进度日志）
# 参数：长边封顶 1280、竖屏降到 720×1280、H.264 CRF30 + faststart
# 日志写入 _compress_log.txt，可实时 tail -f 查看
set -u

FF="/c/Program Files/ffmpeg/bin/ffmpeg.exe"
LOG="_compress_log.txt"

files=(
 "assets/末龙之烬/末龙22集粗剪.mp4"
 "assets/末龙之烬/末龙23集粗剪.mp4"
 "assets/末龙之烬/末龙24集粗剪.mp4"
 "assets/荆木庄园的血誓/荆木庄园的血誓EP19.mp4"
 "assets/荆木庄园的血誓/荆木庄园的血誓EP20.mp4"
 "assets/drama-dushou/video.mp4"
 "assets/drama-xiesi/video.mp4"
 "assets/drama-yuxiang/video.mp4"
 "xinxi-yimei.mp4"
 "xinxi-yanbu.mp4"
 "koubo-kafei.mp4"
 "xinxi-ganfa.mp4"
 "xinxi-xiangfen.mp4"
 "xinxi-yumixu.mp4"
 "vlog-mashu.mp4"
 "jieshuo-chimi.mp4"
 "游戏账号数据/蛋仔官服大神活动.mp4"
 "游戏账号数据/蛋仔惊魂夜宣发.mp4"
)

total=${#files[@]}
echo "==== 视频压缩开始 $(date) | 共 $total 个 ====" > "$LOG"

orig_total=0
new_total=0
done=0
for f in "${files[@]}"; do
  idx=$((done+1))
  orig=$(wc -c < "$f")
  orig_mb=$(awk "BEGIN{printf \"%.2f\", $orig/1048576}")
  orig_total=$((orig_total+orig))
  echo "[$(date +%H:%M:%S)] ($idx/$total) 开始: $f  [原 ${orig_mb} MB]" >> "$LOG"
  tmp="$f.cmp.mp4"
  rm -f "$tmp"
  "$FF" -y -i "$f" \
    -vf "scale=1280:1280:force_original_aspect_ratio=decrease" \
    -c:v libx264 -crf 30 -preset medium -pix_fmt yuv420p \
    -c:a aac -b:a 128k -movflags +faststart \
    "$tmp" >> "$LOG" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -s "$tmp" ]; then
    mv -f "$tmp" "$f"
    new=$(wc -c < "$f")
    new_mb=$(awk "BEGIN{printf \"%.2f\", $new/1048576}")
    new_total=$((new_total+new))
    pct=$(awk "BEGIN{printf \"%.0f\", (1-$new/$orig)*100}")
    echo "[$(date +%H:%M:%S)] ($idx/$total) 完成: $f  ${orig_mb}MB -> ${new_mb}MB  (减小 ${pct}%)" >> "$LOG"
  else
    echo "[$(date +%H:%M:%S)] ($idx/$total) 失败 rc=$rc，保留原片 $f" >> "$LOG"
    rm -f "$tmp"
  fi
  done=$((done+1))
done

orig_gb=$(awk "BEGIN{printf \"%.1f\", $orig_total/1048576}")
new_gb=$(awk "BEGIN{printf \"%.1f\", $new_total/1048576}")
allpct=$(awk "BEGIN{printf \"%.0f\", (1-$new_total/$orig_total)*100}")
echo "==== 压缩结束 $(date) ====" >> "$LOG"
echo "原始总计 ${orig_gb} MB -> 压缩后 ${new_gb} MB  (整体减小 ${allpct}%)" >> "$LOG"
