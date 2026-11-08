#!/usr/bin/env python3
"""最後のちょこ抽出 → 63tube公開（2026-11-07・卒業前の追加素材）.

入力:
  1. iPhone新規分: data/known_profiles/scan-2026-11-choco.json（scan-2026-11.py出力）
     - <5分: 全体エンコード / 5分+: セグメント毎
  2. 11/6ライブ分: ちょこ検出済み5本 — キャッシュフレームからセグメント抽出→カット
出力:
  choco/ に <date>_<stem>[_sXXXXX-eXXXXX].mp4（HDRはHEVC10bit+SDフォールバック）
"""
import csv
import json
import subprocess
from pathlib import Path

ARCHIVE = Path("/Users/sinya/vibecoding/63archive")
CHOCO_JSON = ARCHIVE / "data/known_profiles/scan-2026-11-choco.json"
LIVES = Path("/Volumes/SUNEAST2TB/63archive/data/instagram/63osihaisin/lives")
CACHE = ARCHIVE / "data/face-cache"
CHOCO_DIR = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
FF = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
CHOCO = "choco_burlesque"
COLOR_TAGS = "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc"
# TCC回避: BCはこのセッションから直接読めない為、常駐rclone(:8083)経由で読む
BC_HTTP = "http://media:58981aebdddab3783df6e311@127.0.0.1:8083"


def via_rclone(p: str) -> str:
    """BCボリュームのパスをrclone-http URLに読み替え（他はそのまま）。"""
    if p.startswith("/Volumes/BarraCuda8TB/"):
        return BC_HTTP + "/" + p[len("/Volumes/BarraCuda8TB/"):]
    return p

# 11/6ライブ: ちょこ検出済み（scan結果から）
LIVE_STEMS = [
    "20261106-1820_63osihaisin",
    "20261106-2020_63osihaisin",
    "20261106-2020_63osihaisin-2",
    "20261106-2230_63osihaisin",
    "20261106-2230_63osihaisin-3",
]


def probe(p: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_entries",
                        "stream=width,height,color_primaries,color_transfer:stream_side_data:format=duration",
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
            or v.get("color_transfer") in ("arib-std-b67", "smpte2084"),
            "dur": float(d["format"]["duration"])}


def segments_of(times: list[float], dur: float, iv: float) -> list[tuple[float, float]]:
    if not times:
        return []
    pad = max(15.0, iv)
    segs, s_prev, t_start = [], times[0], times[0]
    for t in times[1:]:
        if t - s_prev > 60:
            segs.append((t_start, s_prev))
            t_start = t
        s_prev = t
    segs.append((t_start, s_prev))
    return [(max(0.0, a - pad), min(dur, b + pad)) for a, b in segs]


def encode(src, out: Path, info: dict, ss: float | None, to: float | None) -> None:
    if out.exists() and out.stat().st_size > 0:
        return
    rot = "transpose=1," if info["w"] > info["h"] else ""
    geo = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
           "pad=1080:1920:(ow-iw)/2:(oh-ih)/2")
    cmd = [FF, "-y"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.2f}", "-t", f"{to - ss:.2f}"]
    cmd += ["-i", src]
    if info["hdr"]:
        cmd += ["-vf", rot + geo, "-pix_fmt", "yuv420p10le",
                "-c:v", "libx265", "-preset", "medium", "-crf", "16",
                "-x265-params", COLOR_TAGS, "-tag:v", "hvc1",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    else:
        cmd += ["-vf", rot + geo + ",hqdn3d=1.5:1.2:3:3",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                "-maxrate", "16M", "-bufsize", "32M",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"✗ {out.name}: {r.stderr.decode()[-200:]}")


def main():
    import warnings
    warnings.filterwarnings("ignore")
    import cv2
    import numpy as np
    from insightface.app import FaceAnalysis

    db = json.loads((ARCHIVE / "data/known_profiles/faces_v3.json").read_text())
    emb = np.stack([np.array(e, dtype=np.float32)
                    for e in db[CHOCO]["embeddings"]])
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    def detect_times(stem: str, iv: float) -> list[float]:
        cache = CACHE / f"{stem}_{iv}s"
        if not cache.exists():
            return []
        times = []
        for i, fp in enumerate(sorted(cache.glob("f*.jpg"))):
            img = cv2.imread(str(fp))
            if img is None:
                continue
            for face in app.get(img):
                if float(np.max(emb @ face.normed_embedding)) >= 0.45:
                    times.append(i * iv)
                    break
        return times

    # --- 1. iPhone新規分 ---
    if CHOCO_JSON.exists():
        hits = json.loads(CHOCO_JSON.read_text())
        print(f"iPhone陽性: {len(hits)}本")
        for h in hits:
            src = h["p"]
            src = via_rclone(src) if src.startswith("http") else via_rclone(src)
            info = probe(src)
            date = h["date"]
            if h["dur"] < 300:
                out = CHOCO_DIR / f"{date}_{h['stem']}.mp4"
                encode(src, out, info, None, None)
                if info["hdr"]:
                    encode(src, CHOCO_DIR / f"{date}_{h['stem']}.sd.mp4", info, None, None)
                print(f"→ {out.name} [{'HDR' if info['hdr'] else 'SDR'}]")
            else:
                for j, (a, b) in enumerate(h["segs"], 1):
                    out = CHOCO_DIR / f"{date}_{h['stem']}_s{int(a):05d}-e{int(b):05d}.mp4"
                    encode(src, out, info, a, b)
                    print(f"→ {out.name} [seg{j}]")

    # --- 2. 11/6ライブ分 ---
    print("ライブ分:")
    for stem in LIVE_STEMS:
        src = LIVES / f"{stem}.mp4"
        if not src.exists():
            continue
        times = detect_times(stem, 5.0)
        if not times:
            print(f"  - {stem}: ちょこ0（スキップ）")
            continue
        info = probe(src)
        segs = segments_of(times, info["dur"], 5.0)
        for j, (a, b) in enumerate(segs, 1):
            out = CHOCO_DIR / f"20261106_{stem}_s{int(a):05d}-e{int(b):05d}.mp4"
            encode(src, out, info, a, b)
            print(f"→ {out.name} [{len(times)}f→{len(segs)}セグの{j}番]")

    n = len(list(CHOCO_DIR.glob("20261106*.mp4"))) + len(list(CHOCO_DIR.glob("2026-11*.mp4")))
    print(f"\n=== 追加完了（11月分: {n}ファイル） ===")


if __name__ == "__main__":
    main()
