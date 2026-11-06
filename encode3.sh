#!/bin/bash
# 第3パス: オリジナルマスター(data/choco-export)から一発エンコード
# - 暗い高ISOノイズ対策にhqdn3d（時間軸優先の軽いノイズ除去）
# - crf24 + maxrate 2.5M + 音声128k（品質優先・総量は後で確認）
set -e
EXPORT="/Volumes/SUNEAST2TB/63archive/data/choco-export"
SRC="/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco"
OUT="$SRC/_publish3"
mkdir -p "$OUT"
export PATH=/opt/homebrew/bin:$PATH

find_original() {
  # 公開名のstem → choco-export内のオリジナルを探す
  local stem="$1"
  # そのまま同名（.mov/.mp4）
  for f in "$EXPORT/$stem.mov" "$EXPORT/$stem.mp4"; do
    [ -f "$f" ] && { echo "$f"; return; }
  done
  # 特殊マップ（初期変換名 → export名）
  case "$stem" in
    "2019-10-10_23-43-00_ChocoBaaam") ls "$EXPORT"/20191010_*ChocoBaaam*.mov 2>/dev/null | head -1; return;;
    "IMG_1193_ChocoPole") ls "$EXPORT"/20220225_IMG_1193*.mov 2>/dev/null | head -1; return;;
    "IMG_3270_Choco") ls "$EXPORT"/*IMG_3270*.mov 2>/dev/null | head -1; return;;
  esac
  # それ以外: stem前方一致（日付プレフィックス違いを吸収）
  ls "$EXPORT/${stem%%_*}"*.mp4 "$EXPORT/${stem%%_*}"*.mov 2>/dev/null | head -1
}

for pub in "$SRC"/*.mp4; do
  [ -f "$pub" ] || continue
  stem="$(basename "${pub%.*}")"
  [ -s "$OUT/$stem.mp4" ] && continue
  orig="$(find_original "$stem")"
  if [ -z "$orig" ] || [ ! -f "$orig" ]; then
    echo "⚠ オリジナル無し: $stem（現行版を流用）"
    cp "$pub" "$OUT/$stem.mp4"
    continue
  fi

  read -r W H ROT <<< "$(ffprobe -v error -print_format json -show_entries stream=width,height:stream_side_data=rotation "$orig" | python3 -c "
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
    VF="transpose=1,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,hqdn3d=1.5:1.2:3:3"
  else
    VF="scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,hqdn3d=1.5:1.2:3:3"
  fi

  echo "→ $stem.mp4 ($W x $H) ← $(basename "$orig")"
  nice -n 10 ffmpeg -y -i "$orig" -vf "$VF" \
    -c:v libx264 -preset medium -crf 24 -maxrate 2.5M -bufsize 5M \
    -c:a aac -b:a 128k -movflags +faststart "$OUT/$stem.mp4" 2>/dev/null
done

echo "=== 完成 ==="
du -sh "$OUT"
ls "$OUT" | wc -l | xargs echo "ファイル数:"
