#!/bin/bash
# 第2パス: _publish(1080p中間) → _publish2（250MB総量目标: crf26 + maxrate 1.5M + 音声96k）
set -e
SRC="/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco/_publish"
OUT="/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco/_publish2"
mkdir -p "$OUT"
export PATH=/opt/homebrew/bin:$PATH

for f in "$SRC"/*.mp4; do
  [ -f "$f" ] || continue
  out="$OUT/$(basename "$f")"
  [ -s "$out" ] && continue
  nice -n 10 ffmpeg -y -i "$f" \
    -c:v libx264 -preset medium -crf 26 -maxrate 1.5M -bufsize 3M \
    -c:a aac -b:a 96k -movflags +faststart "$out" 2>/dev/null
  echo "✓ $(basename "$f")"
done

echo "=== 完成 ==="
du -sh "$OUT"
ls "$OUT" | wc -l | xargs echo "ファイル数:"
