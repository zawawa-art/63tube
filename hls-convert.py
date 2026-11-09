#!/usr/bin/env python3
"""63tube 全動画のHLSアダプティブ化（追いかけ・2026-11-09）.

ラダー（HDR=HEVC 10bit HLG / SDR=H.264）:
  high = 既存mp4を -c copy で分割（無劣化・瞬間）
  mid  = 5Mbps再エンコ（LTE向け）
  low  = 2.5Mbps・720x1280（弱電場向け）

セグメントはfMP4を .mp4 拡張子で（CFのデフォルトキャッシュ対象にする為）。
出力: choco/hls/<stem>/{master.m3u8, high/mid/low.m3u8, seg.*.mp4}
"""
import json
import subprocess
import sys
from pathlib import Path

CHOCO = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
HLS = CHOCO / "hls"
FF = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
COLOR_TAGS = "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc"
SEG = "-hls_time", "4", "-hls_playlist_type", "vod", "-hls_segment_type", "fmp4", "-hls_flags", "independent_segments"


def codec_of(p: Path) -> str:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_entries", "stream=codec_name", str(p)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    return next(s["codec_name"] for s in d["streams"]
                if s["codec_name"] in ("hevc", "h264"))


def gen(name: str):
    src = CHOCO / name
    out = HLS / src.stem
    master = out / "master.m3u8"
    if master.exists():
        return  # 冪等
    out.mkdir(parents=True, exist_ok=True)
    vcodec = codec_of(src)
    is_hdr = vcodec == "hevc"

    # high: stream copy
    r = subprocess.run([FF, "-y", "-i", str(src), "-c", "copy",
                        *SEG, "-hls_fmp4_init_filename", "init.h.mp4",
                        "-hls_segment_filename", "seg.h.%05d.mp4",
                        "high.m3u8"], capture_output=True, cwd=out)
    if r.returncode != 0:
        print(f"✗ high {name}: {r.stderr.decode()[-150:]}")
        return

    # mid: 5Mbps
    if is_hdr:
        vcmd = ["-c:v", "libx265", "-preset", "medium", "-crf", "24",
                "-maxrate", "5M", "-bufsize", "10M",
                "-x265-params", COLOR_TAGS, "-tag:v", "hvc1"]
    else:
        vcmd = ["-c:v", "libx264", "-preset", "medium", "-crf", "22",
                "-maxrate", "5M", "-bufsize", "10M"]
    subprocess.run([FF, "-y", "-i", str(src), *vcmd,
                    "-c:a", "aac", "-b:a", "128k", *SEG,
                    "-hls_fmp4_init_filename", "init.m.mp4",
                    "-hls_segment_filename", "seg.m.%05d.mp4",
                    "mid.m3u8"], capture_output=True, cwd=out)

    # low: 2.5Mbps・720x1280
    if is_hdr:
        vcmd = ["-vf", "scale=720:1280", "-pix_fmt", "yuv420p10le",
                "-c:v", "libx265", "-preset", "medium", "-crf", "26",
                "-maxrate", "2500k", "-bufsize", "5M",
                "-x265-params", COLOR_TAGS, "-tag:v", "hvc1"]
    else:
        vcmd = ["-vf", "scale=720:1280",
                "-c:v", "libx264", "-preset", "medium", "-crf", "24",
                "-maxrate", "2500k", "-bufsize", "5M"]
    subprocess.run([FF, "-y", "-i", str(src), *vcmd,
                    "-c:a", "aac", "-b:a", "96k", *SEG,
                    "-hls_fmp4_init_filename", "init.l.mp4",
                    "-hls_segment_filename", "seg.l.%05d.mp4",
                    "low.m3u8"], capture_output=True, cwd=out)

    # master.m3u8
    dur_bps = src.stat().st_size * 8 / max(1, 1)
    bw_high = int(src.stat().st_size * 8 / _dur(src)) + 200000
    codecs = "hvc1.2.4.L153.B0,mp4a.40.2" if is_hdr else "avc1.640028,mp4a.40.2"
    master.write_text(f"""#EXTM3U
#EXT-X-VERSION:7
#EXT-X-STREAM-INF:BANDWIDTH={bw_high},CODECS="{codecs}",RESOLUTION=1080x1920
high.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5500000,CODECS="{codecs}",RESOLUTION=1080x1920
mid.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2800000,CODECS="{codecs}",RESOLUTION=720x1280
low.m3u8
""")
    print(f"✓ {src.stem[:44]}")


def _dur(p: Path) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    vj = json.load(open("/Users/sinya/vibecoding/63tube/videos.json"))
    names = [v["url"].split("/")[-1].split("?")[0] for v in vj]
    names = [n for n in names if (CHOCO / n).exists()]
    print(f"対象: {len(names)}本")
    for i, n in enumerate(names):
        gen(n)
        if (i + 1) % 10 == 0:
            print(f"... {i + 1}/{len(names)}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
