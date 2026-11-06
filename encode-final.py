#!/usr/bin/env python3
"""卒業記念 最終エンコード（HDR対応版）.

- HDRソース（HLG/bt2020）32本:
    本命   = HEVC 10bit（HLGそのまま保持）→ HDR対応スマホで本来の輝度
             x265 crf16 medium + hvc1タグ + bt2020/HLGシグナリング
    予備   = H.264 8bit（HLGシグナリング付き）→ HEVC非対応端末向け
             （HLGはSDR画面でも概ね見える後方互換設計）
- SDRソース 6本:
    H.264 crf18 slow + hqdn3d（従来どおり最高画質）

manifest.csvで公開名→マスターを正確に解決（encode3.pyの実績ベース）。
"""
import csv
import json
import shutil
import subprocess
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
COLOR_TAGS = "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc"


def load_manifest() -> dict:
    man = {}
    for r in csv.DictReader(open(EXPORT / "manifest.csv")):
        man[r["file"]] = (r["source"], int(r["seg_start_s"] or 0),
                          int(r["seg_end_s"] or 0), r["mode"])
    return man


def probe(p: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_entries",
                        "stream=width,height,color_primaries,color_transfer:stream_side_data",
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
    hdr = (v.get("color_primaries") == "bt2020"
           or v.get("color_transfer") in ("arib-std-b67", "smpte2084"))
    return {"w": w, "h": h, "hdr": hdr}


def main():
    man = load_manifest()
    OUT.mkdir(exist_ok=True)
    for pub in sorted(SRC.glob("*.mp4")):
        stem = pub.stem
        main_out = OUT / f"{stem}.mp4"
        sd_out = OUT / f"{stem}.sd.mp4"
        mkey = SPECIAL.get(stem) or next(
            (f"{stem}{e}" for e in (".mov", ".mp4") if f"{stem}{e}" in man), None)
        if not mkey or mkey not in man:
            print(f"⚠ 解決不能: {stem}")
            continue
        src_path, ss, ee, mode = man[mkey]
        src = Path(src_path)
        if not src.exists():
            print(f"⚠ ソース不在: {stem}")
            continue
        info = probe(src)
        rot = "transpose=1," if info["w"] > info["h"] else ""
        geo = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2")

        seek = []
        if mode.startswith("cut"):
            seek = ["-ss", str(ss), "-t", str(ee - ss)]
        kind = "HDR" if info["hdr"] else "SDR"

        # --- 本命 ---
        if not main_out.exists() or main_out.stat().st_size == 0:
            if info["hdr"]:
                cmd = [FF, "-y", *seek, "-i", str(src),
                       "-vf", rot + geo, "-pix_fmt", "yuv420p10le",
                       "-c:v", "libx265", "-preset", "medium", "-crf", "16",
                       "-x265-params", COLOR_TAGS,
                       "-tag:v", "hvc1",
                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                       str(main_out)]
            else:
                cmd = [FF, "-y", *seek, "-i", str(src),
                       "-vf", rot + geo + ",hqdn3d=1.5:1.2:3:3",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                       "-maxrate", "16M", "-bufsize", "32M",
                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                       str(main_out)]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                print(f"✗ {stem}: {r.stderr.decode()[-200:]}")
                continue
        # --- HDRのSDRフォールバック ---
        if info["hdr"] and not sd_out.exists():
            cmd = [FF, "-y", *seek, "-i", str(src),
                   "-vf", rot + geo + ",hqdn3d=1.5:1.2:3:3",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                   "-x264-params", COLOR_TAGS,
                   "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                   str(sd_out)]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                print(f"✗ SD分 {stem}: {r.stderr.decode()[-200:]}")
                continue
        print(f"→ {stem}.mp4 [{kind}{'+sd' if info['hdr'] else ''}]"
              f"{'+cut' if mode.startswith('cut') else ''}")
    subprocess.run(["du", "-sh", str(OUT)])
    n_sd = len(list(OUT.glob("*.sd.mp4")))
    print(f"完成: 本命{len(list(OUT.glob('*.mp4'))) - n_sd}本 / SDRフォールバック{n_sd}本")


if __name__ == "__main__":
    main()
