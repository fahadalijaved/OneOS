#!/usr/bin/env python3
"""A phone's picture for Nothing OS's About phone, from a product photo.

Takes a photo of the phone on a plain light background (the owner's product
shots), makes the background transparent (flood fill from the edges, so a white
phone body keeps its pixels as long as an edge line separates it), splits the
shot into the phones it shows (columns of background between them; slivers such
as an S Pen are dropped) and lays the back and the front over each other like
the Z Fold8 Ultra's picture (switcher/overlays/nothing_about), on a 423 x 882
transparent canvas (xxhdpi). Needs Pillow.

Usage: make-about-picture.py <photo> <out.png> [--split 0.5] [--overlap 0.45]
  --split F   cut the shot at this fraction of its width when the phones touch
              (the Z Fold8's back and inner screen)
  --overlap F how much of the first phone the second covers (default 0.45);
              0 keeps the shot as one piece
"""
import argparse

from PIL import Image, ImageDraw, ImageFilter

W, H = 423, 882
KEY = (255, 0, 255)


def transparent(img, tol):
    rgb = img.convert("RGB")
    w, h = rgb.size
    seeds = [(x, 0) for x in range(0, w, 8)] + [(x, h - 1) for x in range(0, w, 8)] + \
            [(0, y) for y in range(0, h, 8)] + [(w - 1, y) for y in range(0, h, 8)]
    for s in seeds:
        if rgb.getpixel(s) != KEY:
            ImageDraw.floodfill(rgb, s, KEY, thresh=tol)
    mask = Image.new("L", (w, h), 255)
    mask.putdata([0 if p == KEY else 255 for p in rgb.getdata()])
    # Soften the cut edge by a pixel.
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def segments(img, min_frac):
    """Column ranges holding the phones, left to right."""
    a = img.getchannel("A")
    w, h = a.size
    cols = [max(a.crop((x, 0, x + 1, h)).getdata()) > 40 for x in range(w)]
    segs, start = [], None
    for x, c in enumerate(cols + [False]):
        if c and start is None:
            start = x
        elif not c and start is not None:
            segs.append((start, x))
            start = None
    return [s for s in segs if s[1] - s[0] >= min_frac * w]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("out")
    ap.add_argument("--split", type=float, default=0.0)
    ap.add_argument("--overlap", type=float, default=0.45)
    ap.add_argument("--tol", type=int, default=18)
    a = ap.parse_args()

    img = transparent(Image.open(a.photo), a.tol)
    if a.split:
        x = int(img.width * a.split)
        parts = [img.crop((0, 0, x, img.height)), img.crop((x, 0, img.width, img.height))]
    else:
        parts = [img.crop((s[0], 0, s[1], img.height)) for s in segments(img, 0.12)]
    parts = [p.crop(p.getbbox()) for p in parts if p.getbbox()]
    if a.overlap and len(parts) >= 2:
        back, front = parts[-2], parts[-1]
        dx = int(back.width * (1 - a.overlap))
        top = max(back.height, front.height)
        comp = Image.new("RGBA", (dx + front.width, top), (0, 0, 0, 0))
        comp.alpha_composite(back, (0, (top - back.height) // 2))
        comp.alpha_composite(front, (dx, (top - front.height) // 2))
    else:
        comp = img.crop(img.getbbox())
    s = min(W / comp.width, H / comp.height)
    comp = comp.resize((max(1, int(comp.width * s)), max(1, int(comp.height * s))), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(comp, ((W - comp.width) // 2, (H - comp.height) // 2))
    canvas.save(a.out, optimize=True)
    print("wrote %s: %d part(s), picture %d x %d" % (a.out, len(parts), comp.width, comp.height))


if __name__ == "__main__":
    main()
