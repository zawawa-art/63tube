#!/usr/bin/env python3
"""videos.json に url_hls を追加（in-place・タイトル等の手動編集を保持）."""
import json
from pathlib import Path

CHOCO = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
VJ = Path("/Users/sinya/vibecoding/63tube/videos.json")

d = json.loads(VJ.read_text())
n = 0
for v in d:
    fname = v["url"].split("/")[-1].split("?")[0]
    stem = Path(fname).stem
    master = CHOCO / "hls" / stem / "master.m3u8"
    if master.exists():
        v["url_hls"] = f"https://pub.zawawa.uk/63tube/choco/hls/{stem}/master.m3u8?v=1"
        n += 1
    else:
        v.pop("url_hls", None)  # 無ければ消す（再実行で整理）
VJ.write_text(json.dumps(d, ensure_ascii=False, indent=2))
print(f"url_hls追加: {n}/{len(d)}本")
