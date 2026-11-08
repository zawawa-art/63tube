#!/usr/bin/env python3
"""63tube videos.json 生成 — _publish/ の完成mp4から実測メタデータで書き出す.

- 全ファイル 1080x1920 縦前提（encode.sh の出力）
- 日付はファイル名の YYYYMMDD プレフィックスから（無いものは固定マップ）
- タイトルはステムから日付・時刻・ID・区間を除去して整形
- 日付昇順（デビュー→直近の流れ）で choco-001.. と採番
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SRC = Path("/Volumes/SUNEAST2TB/pub.zawawa.uk/63tube/choco")
OUT = Path(__file__).resolve().parent / "videos.json"

# ファイル名に日付が無いもの（既知の対応）
FIXED_DATES = {
    "IMG_1193_ChocoPole": "2022-02-25",
    "IMG_3270_Choco": "2022-03-15",
}
SPECIAL_TITLES = {
    "ChocoBaaam": "ChocoBaaam — デビュー8日後の貴重な姿",
}


def probe(p: Path) -> tuple[int, int, int]:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_entries", "stream=width,height:format=duration", str(p)],
        capture_output=True, text=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s.get("width"))
    dur = round(float(d["format"]["duration"]))
    return v["width"], v["height"], dur


def date_of(stem: str) -> str:
    m = re.match(r"^(20\d{2})(\d{2})(\d{2})_", stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"^(20\d{2}-\d{2}-\d{2})_", stem)
    if m:
        return m.group(1)
    for k, v in FIXED_DATES.items():
        if stem.startswith(k):
            return v
    return ""


def title_of(stem: str) -> str:
    # ライブ録画セグメント: 卒業前配信 N部
    if "63osihaisin" in stem:
        m = re.search(r"-(1820|2020|2230)_", stem)
        bu = {"1820": "1部", "2020": "2部", "2230": "3部"}.get(
            m.group(1) if m else "", "")
        return f"卒業前配信 {bu}"
    for k, v in SPECIAL_TITLES.items():
        if k in stem:
            return v
    s = stem
    s = re.sub(r"^(20\d{6}_)+", "", s)          # 先頭のYYYYMMDD_（重複も）
    s = re.sub(r"^(20\d{2}-\d{2}-\d{2})_", "", s)
    s = re.sub(r"^\d{2}-\d{2}-\d{2}_", "", s)    # 撮影時刻 HH-MM-SS_
    s = re.sub(r"_s\d{4,5}-e\d{4,5}$", "", s)    # セグメント区間
    s = re.sub(r"_[0-9a-f]{6}$", "", s)          # clip_id末尾
    s = re.sub(r"_trim$", "", s)                 # QTトリム版接尾辞
    s = s.replace("_", " ").strip()
    return s or stem


def main():
    files = sorted(SRC.glob("*.mp4"))
    files = [f for f in files if not f.name.endswith(".sd.mp4")]  # フォールバックは除外
    if not files:
        sys.exit("mp4がありません")
    entries = []
    for f in files:
        stem = f.stem
        w, h, dur = probe(f)
        d = date_of(stem)
        entries.append({
            "date": d, "file": f.name, "w": w, "h": h, "dur": dur,
            "title": title_of(stem)})
    entries.sort(key=lambda e: (e["date"], e["file"]))
    out = []
    for i, e in enumerate(entries, 1):
        entry = {
            "id": f"choco-{i:03d}",
            "cast": "choco",
            "title": e["title"],
            "date": e["date"],
            "url": f"https://pub.zawawa.uk/63tube/choco/{e['file']}?v=3",
            "duration": e["dur"],
            "width": e["w"],
            "height": e["h"],
            "orientation": "portrait",
        }
        sd = SRC / e["file"].replace(".mp4", ".sd.mp4")
        if sd.exists():
            entry["url_sd"] = f"https://pub.zawawa.uk/63tube/choco/{sd.name}?v=3"
        out.append(entry)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    total = sum(e["dur"] for e in entries)
    print(f"{len(out)}本 / 計{total}秒 / 保存: {OUT}")


if __name__ == "__main__":
    main()
