#!/usr/bin/env python3
"""追加8本の統一変換 — 縦1080x1920・HDR dual・512MB以下・faststart."""
import json
import subprocess
from pathlib import Path

CHOCO = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
FF = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
COLOR_TAGS = "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc"

TARGETS = [
    "20200603_20200603_第7世代_BurlesqueTOKYO_FBLIVE_6ef882_s01200-e01320_trim.mp4",
    "20210207_2021-02-07_22-59-40_ChocoPole_IMG_8204_03776a.mov",
    "20210208_2021-02-08_00-01-06_IMG_8270_ef8164.mov",
    "20210322_2021-03-22_21-53-13_ChocoPole_IMG_1628_de140e.mov",
    "20210731_2021-07-31_15-40-21_IMG_0862_17cb36_trim.mp4",
    "20211118_2021-11-18_19-22-16_IMG_4657_808988_trim.mov",
    "20240829_2024-08-29_20-59-32_IMG_2628_659b60_trim.mov",
    "20250123_2025-01-23_21-08-20_IMG_3056_37ded5_trim.mov",
]


def probe(p: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_entries", "stream=codec_name,width,height,color_primaries,color_transfer:stream_side_data:format=duration",
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
    return {"w": w, "h": h, "hdr": v.get("color_primaries") == "bt2020"
            or v.get("color_transfer") in ("arib-std-b67", "smpte2084")}


def encode(src: Path, out: Path, info: dict) -> None:
    rot = "transpose=1," if info["w"] > info["h"] else ""
    geo = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
           "pad=1080:1920:(ow-iw)/2:(oh-ih)/2")
    if info["hdr"]:
        cmd = [FF, "-y", "-i", str(src), "-vf", rot + geo,
               "-pix_fmt", "yuv420p10le",
               "-c:v", "libx265", "-preset", "medium", "-crf", "16",
               "-x265-params", COLOR_TAGS, "-tag:v", "hvc1",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    else:
        cmd = [FF, "-y", "-i", str(src), "-vf", rot + geo,
               "-c:v", "libx264", "-preset", "slow", "-crf", "18",
               "-maxrate", "16M", "-bufsize", "32M",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"  ✗ {out.name}: {r.stderr.decode()[-150:]}")
        return
    print(f"  ✓ {out.name} {out.stat().st_size/1024**2:.0f}MB")


def main():
    for name in TARGETS:
        src = CHOCO / name
        if not src.exists():
            print(f"?? {name}")
            continue
        info = probe(src)
        out = CHOCO / f"{src.stem}.mp4"
        print(f"[{'HDR' if info['hdr'] else 'SDR'} {'横回転' if info['w'] > info['h'] else '縦'}] {name[:44]}")
        encode(src, out, info)
        if info["hdr"] and out.exists():
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
        if out.exists() and out.stat().st_size > 0 and src != out:
            src.unlink()  # 元（.mov）を削除
    print("done")


if __name__ == "__main__":
    main()
