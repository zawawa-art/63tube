#!/bin/bash
# 63tube公開用エンコード — 全クリップを縦1080x1920 H.264 + faststart に統一
# 横動画は90°回転（transpose=1）。250MB総量目標（crf25 + maxrate 2.2M）。
set -e
SRC="/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco"
OUT="$SRC/_publish"
mkdir -p "$OUT"
export PATH=/opt/homebrew/bin:$PATH

for f in "$SRC"/*.mov "$SRC"/*.mp4; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  [[ "$base" == _* ]] && continue
  out="$OUT/${base%.*}.mp4"
  [ -s "$out" ] && continue  # 冪等

  # 表示向きを判定（ffprobeでrotation込み）
  read -r W H ROT <<< "$(ffprobe -v error -print_format json -show_entries stream=width,height:stream_side_data=rotation "$f" | python3 -c "
import json, sys
d = json.load(sys.stdin)
v = next(s for s in d['streams'] if s.get('width'))
rot = 0
for s in d['streams']:
    for sd in (s.get('side_data_list') or []):
        if 'rotation' in sd: rot = int(sd['rotation'])
w, h = v['width'], v['height']
if rot in (90, -90, 270): w, h = h, w
print(w, h, rot)")"

  if [ "$W" -gt "$H" ]; then
    VF="transpose=1,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
  else
    VF="scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
  fi

  echo "→ ${base%.*}.mp4 ($W x $H)"
  nice -n 10 ffmpeg -y -i "$f" -vf "$VF" \
    -c:v libx264 -preset medium -crf 25 -maxrate 2.2M -bufsize 4.4M \
    -c:a aac -b:a 128k -movflags +faststart "$out" 2>/dev/null
done

echo "=== 完成 ==="
du -sh "$OUT"
ls "$OUT" | wc -l | xargs echo "ファイル数:"
