#!/usr/bin/env python3
"""第3パス（やり直し）: manifest.csvで公開名→ソースを正確に解決して
マスターから一発エンコード。卒業記念最終版: crf18/slow/16M・音声192k。

解決ルール:
- 公開stem → manifestのfile列（同名.mov/.mp4）→ source + セグメント区間
- 特殊3本（初期変換名）は固定マップ
- 解決不能なものだけ現行版を流用（警告付き）
"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

EXPORT = Path("/Volumes/SUNEAST2TB/63archive/data/choco-export")
SRC = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
OUT = SRC / "_final"
FF = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

SPECIAL = {
    "2019-10-10_23-43-00_ChocoBaaam": "20191010_2019-10-10_23-43-00_ChocoBaaam_85732f.mov",
    "IMG_1193_ChocoPole": "20220225_IMG_1193_ChocoPole_682507.mov",
    "IMG_3270_Choco": "20220315_IMG_3270_Choco_c6e636.mov",
}


def load_manifest() -> dict:
    man = {}
    for r in csv.DictReader(open(EXPORT / "manifest.csv")):
        man[r["file"]] = (r["source"], int(r["seg_start_s"] or 0),
                          int(r["seg_end_s"] or 0), r["mode"])
    return man


def dims_with_rotation(p: Path) -> tuple[int, int]:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_entries", "stream=width,height:stream_side_data=rotation",
                        str(p)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s.get("width"))
    rot = 0
    for s in d["streams"]:
        for sd in (s.get("side_data_list") or []):
            if "rotation" in sd:
                rot = int(sd["rotation"])
    w, h = v["width"], v["height"]
    if rot in (90, -90, 270):
        w, h = h, w
    return w, h


def main():
    man = load_manifest()
    OUT.mkdir(exist_ok=True)
    n_ok = n_keep = 0
    for pub in sorted(SRC.glob("*.mp4")):
        stem = pub.stem
        out = OUT / f"{stem}.mp4"
        if out.exists() and out.stat().st_size > 0:
            continue
        mkey = SPECIAL.get(stem)
        if not mkey:
            for ext in (".mov", ".mp4"):
                if f"{stem}{ext}" in man:
                    mkey = f"{stem}{ext}"
                    break
        if not mkey or mkey not in man:
            print(f"⚠ manifest解決不能: {stem} → 現行版流用")
            shutil.copyfile(pub, out)
            n_keep += 1
            continue
        src_path, ss, ee, mode = man[mkey]
        if not Path(src_path).exists():
            print(f"⚠ ソース不在: {stem} ← {src_path} → 現行版流用")
            shutil.copyfile(pub, out)
            n_keep += 1
            continue

        w, h = dims_with_rotation(Path(src_path))
        vf = ("transpose=1," if w > h else "") + \
             "scale=1080:1920:force_original_aspect_ratio=decrease," \
             "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,hqdn3d=1.5:1.2:3:3"
        cmd = [FF, "-y"]
        if mode.startswith("cut"):
            cmd += ["-ss", str(ss), "-t", str(ee - ss)]
        cmd += ["-i", src_path, "-vf", vf,
                "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                "-maxrate", "16M", "-bufsize", "32M",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                str(out)]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            print(f"✗ エンコード失敗: {stem}: {r.stderr.decode()[-200:]}")
            continue
        n_ok += 1
        print(f"→ {stem}.mp4 ({'横回転' if w > h else '縦'}"
              f"{'+カット' + str(ee - ss) + 's' if mode.startswith('cut') else ''})"
              f" ← {Path(src_path).name[:40]}")
    print(f"\n=== 完成: 新規{n_ok} + 流用{n_keep} ===")
    subprocess.run(["du", "-sh", str(OUT)])


if __name__ == "__main__":
    main()
