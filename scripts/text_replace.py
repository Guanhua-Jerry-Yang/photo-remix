#!/usr/bin/env python3
"""photo-remix 改字：只替换图中一块文字，其余像素不动（不重新生成）。

找位置: text_replace.py find <img> x0,y0,x1,y1 [--dark]
        在给定区域里找亮色（或 --dark 暗色）文字的精确外框
替换:   text_replace.py put <img> --out <out.png> --box x0,y0,x1,y1 --text 新字 [--height 24] [--center]
        [--color 238,238,240] [--weight W6|W3] [--font 路径]
        --box 是原文字外框（find 的结果），先用四周背景双线性填平，再写新字；
        --height 默认等于原框高；--center 以原框中心居中，否则左对齐原框；可重复多组 --box/--text
"""
import argparse, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = {"W6": ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2),
         "W3": ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0)}


def find(img, box, dark=False, th=200):
    a = np.array(Image.open(img).convert("RGB")).astype(int)
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1]
    m = (r.max(2) < 255 - th) if dark else (r.min(2) > th)
    ys, xs = np.where(m)
    if not len(xs):
        sys.exit("区域内没找到文字像素，调整区域或阈值")
    print(f"{x0+xs.min()},{y0+ys.min()},{x0+xs.max()},{y0+ys.max()}")


def wipe(a, x0, y0, x1, y1, pad=3):
    o = a.copy()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tx = (x - x0) / max(1, x1 - x0); ty = (y - y0) / max(1, y1 - y0)
            row = o[y, x0 - pad] * (1 - tx) + o[y, x1 + pad] * tx
            col = o[y0 - pad, x] * (1 - ty) + o[y1 + pad, x] * ty
            a[y, x] = (row + col) / 2


def put(a, text, x, y, h, color, font, index, center_x=None):
    # 4 倍渲染 → 缩到目标字高 → 二值化，得到和游戏/海报 UI 接近的硬边字
    f = ImageFont.truetype(font, h * 4, index=index)
    t = Image.new("L", (int(f.getlength(text)) + 20, h * 6), 0)
    ImageDraw.Draw(t).text((0, 0), text, font=f, fill=255)
    t = t.crop(t.getbbox())
    t = t.resize((round(t.width * h / t.height), h), Image.BOX).point(lambda v: 255 if v > 100 else 0)
    if center_x is not None:
        x = int(center_x - t.width / 2)
    m = np.array(t) > 0
    H, W = m.shape
    a[y:y + H, x:x + W][m] = color
    return x, y, x + W, y + H


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "find":
        ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("img"); ap.add_argument("box")
        ap.add_argument("--dark", action="store_true"); a = ap.parse_args()
        return find(a.img, [int(v) for v in a.box.split(",")], a.dark)
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("img"); ap.add_argument("--out", required=True)
    ap.add_argument("--box", action="append", required=True); ap.add_argument("--text", action="append", required=True)
    ap.add_argument("--height", type=int); ap.add_argument("--center", action="store_true")
    ap.add_argument("--color", default="238,238,240"); ap.add_argument("--weight", default="W6")
    ap.add_argument("--font")
    a = ap.parse_args()
    font, index = (a.font, 0) if a.font else FONTS[a.weight]
    color = [int(v) for v in a.color.split(",")]
    arr = np.array(Image.open(a.img).convert("RGB")).astype(float)
    for box, text in zip(a.box, a.text):
        x0, y0, x1, y1 = [int(v) for v in box.split(",")]
        wipe(arr, x0 - 2, y0 - 2, x1 + 2, y1 + 2)
        h = a.height or (y1 - y0 + 1)
        print(text, put(arr, text, x0, y0, h, color, font, index, (x0 + x1) / 2 if a.center else None))
    Image.fromarray(arr.clip(0, 255).astype("uint8")).save(a.out)


if __name__ == "__main__":
    main()
