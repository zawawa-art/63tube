#!/usr/bin/env python3
"""2023-11-09 Apple Log 5本の変換（AppleLog→HLG LUT適用・OCIO公式実装由来）.

- 4本: Apple Log（bt2020/無タグtransfer）→ lut1d(applelog_to_hlg.cube) → HEVC 10bit HLG
- 1本: ネイティブHLG（IMG_3675）→ 通常変換
- 全部: 縦1080x1920・512MB以下・faststart・SD dual
"""
import json
import subprocess
from pathlib import Path

CHOCO = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
LUT = "/Users/sinya/vibecoding/63tube/applelog_to_hlg.cube"
FF = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
COLOR_TAGS = "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc"

LOG_FILES = [
    "2023-11-09_21-11-54_IMG_3646_trim.mov",
    "2023-11-09_21-29-14_IMG_3658.MOV",
    "2023-11-09_21-37-33_IMG_3659_trim.mov",
    "2023-11-09_21-55-01_IMG_3663.MOV",
]
HLG_FILES = ["2023-11-09_22-20-14_IMG_3675.MOV"]


def probe(p: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_entries", "stream=width,height:stream_side_data",
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
    return {"w": w, "h": h}


def convert(src: Path, use_lut: bool):
    info = probe(src)
    rot = "transpose=1," if info["w"] > info["h"] else ""
    geo = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
           "pad=1080:1920:(ow-iw)/2:(oh-ih)/2")
    lut = f"lut1d={LUT}," if use_lut else ""
    out = CHOCO / f"{src.stem}.mp4"
    if out.exists() and out.stat().st_size > 0:
        print(f"skip {out.name}")
        return
    cmd = [FF, "-y", "-i", str(src), "-vf", lut + rot + geo,
           "-pix_fmt", "yuv420p10le",
           "-c:v", "libx265", "-preset", "medium", "-crf", "16",
           "-x265-params", COLOR_TAGS, "-tag:v", "hvc1",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"✗ {out.name}: {r.stderr.decode()[-200:]}")
        return
    print(f"✓ {out.name} {out.stat().st_size/1024**2:.0f}MB"
          f" [{'横回転' if rot else '縦'}]")
    sd = CHOCO / f"{src.stem}.sd.mp4"
    cmd = [FF, "-y", "-i", str(out), "-vf",
           "scale=1080:1920:force_original_aspect_ratio=decrease,"
           "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,hqdn3d=1.5:1.2:3:3",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-x264-params", COLOR_TAGS,
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(sd)]
    subprocess.run(cmd, capture_output=True)
    if sd.exists():
        print(f"  ✓ {sd.name} {sd.stat().st_size/1024**2:.0f}MB")


def main():
    for f in LOG_FILES:
        p = CHOCO / f
        if p.exists():
            convert(p, use_lut=True)
        else:
            print(f"?? {f}")
    for f in HLG_FILES:
        p = CHOCO / f
        if p.exists():
            convert(p, use_lut=False)
        else:
            print(f"?? {f}")
    print("done")


if __name__ == "__main__":
    main()
