#!/bin/bash
# 63tube キュレーション反映 — choco/ の現状を videos.json に反映してライブへ
# 使い方: ./update.sh （MacbookからSSHでもmini上でも）
set -e
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:$PATH
python3 build-videos-json.py
# pub側のフォールバックコピーも更新（Pagesが本命だが念のため）
for f in videos.json; do cat "$f" > "/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/$f"; done
git add -A
git commit -m "curate: choco/ の現状を反映 $(date '+%m-%d %H:%M')" || true
git push origin main
echo "→ https://63tube.zawawa.uk （~30秒で反映）"
