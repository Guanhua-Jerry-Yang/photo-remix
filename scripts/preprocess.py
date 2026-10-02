#!/usr/bin/env python3
"""photo-remix 预处理：建 run 目录、裁掉底部相机水印条、读 EXIF。

用法: preprocess.py --run <run_dir> <photo> [<photo> ...]
产出: <run>/photos/pNN/{source.jpg, strip.jpg(若有水印条), meta.json}
"""
import argparse, json, pathlib, shutil
import numpy as np
from PIL import Image, ImageOps, ExifTags


def find_strip(a):
    """从底部往上找"纯色底+少量文字"的水印条，返回条的起始行；没有则 None。
    判据：每行 ≥70% 像素与条底色相差 ≤8，且条高占 4%–15%；照片里的沙地/天空有纹理过不了。"""
    h = a.shape[0]
    base = np.median(a[-3:].reshape(-1, 3), axis=0)
    y = h - 1
    while y > h * 0.8:
        near = (np.abs(a[y] - base).max(axis=1) <= 8).mean()
        if near < 0.70:
            break
        y -= 1
    top = y - 1  # 多切 2 行，去掉过渡色
    frac = (h - top) / h
    return top if 0.04 <= frac <= 0.15 else None


def exif_info(im):
    out = {}
    try:
        ex = im.getexif()
        for k, v in ex.items():
            name = ExifTags.TAGS.get(k, k)
            if name in ("DateTime", "Make", "Model"):
                out[name] = str(v)
        gps = ex.get_ifd(0x8825)
        if gps:
            def deg(t):
                d, m, s = [float(x) for x in t]
                return d + m / 60 + s / 3600
            lat, lon = deg(gps[2]), deg(gps[4])
            if gps.get(1) == 'S': lat = -lat
            if gps.get(3) == 'W': lon = -lon
            out["gps"] = [round(lat, 5), round(lon, 5)]
    except Exception:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--no-crop", action="store_true")
    a = ap.parse_args()
    run = pathlib.Path(a.run).expanduser()
    (run / "photos").mkdir(parents=True, exist_ok=True)
    existing = sorted(p.name for p in (run / "photos").iterdir() if p.is_dir())
    n = len(existing)
    for src in a.photos:
        src = pathlib.Path(src).expanduser()
        n += 1
        key = f"p{n:02d}"
        d = run / "photos" / key
        (d / "outputs").mkdir(parents=True, exist_ok=True)
        im = Image.open(src)
        meta = {"key": key, "original": str(src), "exif": exif_info(im)}
        im = ImageOps.exif_transpose(im).convert("RGB")
        arr = np.array(im).astype(int)
        top = None if a.no_crop else find_strip(arr)
        if top:
            im.crop((0, top, im.width, im.height)).save(d / "strip.jpg", quality=92)
            im = im.crop((0, 0, im.width, top))
            meta["watermark_strip_cropped_at"] = top
        im.save(d / "source.jpg", quality=95)
        meta["size"] = list(im.size)
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        print(key, src.name, "size", im.size, "strip" if top else "no-strip", meta["exif"])


if __name__ == "__main__":
    main()
