#!/usr/bin/env python3
"""Draw the title and chapter cards as transparent PNGs for finish.sh.

cards.py WIDTH HEIGHT OUTDIR  -> OUTDIR/card_NN.png + OUTDIR/cards.txt
(cards.txt: one "file start duration fade-out-at" line per card, seconds)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LATO = os.path.join(HERE, "assets", "fonts")  # Lato 2.015, SIL OFL 1.1
BIG_FACE = f"{LATO}/Lato-Light.ttf"
SMALL_FACE = f"{LATO}/Lato-Regular.ttf"
LOGO = os.path.join(HERE, "assets", "qtpass-logo.png")
INK = (232, 240, 248, 255)

sys.path.insert(0, HERE)
import shots  # noqa: E402

# (start, end, layout, big line, small line), timed to the world's clock
CARDS = shots.cards()


def tracked(draw, xy, text, font, tracking):
    """Draw text with extra letter spacing; return its width."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=INK)
        x += draw.textlength(ch, font=font) + tracking
    return x - xy[0] - tracking


def width_of(draw, text, font, tracking):
    return sum(draw.textlength(c, font=font) for c in text) + tracking * (len(text) - 1)


def card(w, h, layout, big, small):
    """One card. Layouts: "lower" (a chapter, top left), "centre" (logo and
    name mid-frame) and "low" (the same, smaller, in the lower half, the
    picture above it). A newline in the small line starts another."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    centre = layout in ("centre", "low")
    low = layout == "low"
    bsize = int(h * (0.075 if not centre else 0.10 if low else 0.12))
    ssize = int(h * (0.038 if centre else 0.042))
    bf = ImageFont.truetype(BIG_FACE, bsize)
    sf = ImageFont.truetype(SMALL_FACE, ssize)
    btrack = bsize * (0.03 if centre else 0.02)
    strack = ssize * 0.1
    lines = small.split("\n")
    if centre:
        lh = int(h * (0.13 if low else 0.2))
        top = int(h * (0.49 if low else 0.15))
        logo = Image.open(LOGO).convert("RGBA").resize((lh, lh), Image.LANCZOS)
        img.alpha_composite(logo, ((w - lh) // 2, top))
        by = top + lh + int(h * 0.02)
        bx = (w - width_of(d, big, bf, btrack)) / 2
        sy = by + int(bsize * 1.35)
    else:
        bx, by = int(w * 0.06), int(h * 0.1)
        sy = by + int(bsize * 1.25)
    tracked(d, (bx, by), big, bf, btrack)
    for i, line in enumerate(lines):
        sx = (w - width_of(d, line, sf, strack)) / 2 if centre else bx + int(bsize * 0.04)
        tracked(d, (sx, sy + i * int(ssize * 1.6)), line, sf, strack)
    # under the type: a wide soft shade, so it reads over bright picture
    # too, and a tight shadow for the edge
    alpha = img.getchannel("A")
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for radius, strength in ((h * 0.035, 1.6), (h * 0.006, 0.5)):
        shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        shade.putalpha(alpha.filter(ImageFilter.GaussianBlur(radius))
                       .point(lambda v, k=strength: min(int(v * k), 150)))
        out = Image.alpha_composite(out, shade)
    return Image.alpha_composite(out, img)


def translated(cards):
    """The cards in CARDS_LANG (cards/<lang>.json), when it is set: same
    times and layout, other words. {classes} and {lines} are filled in."""
    lang = os.environ.get("CARDS_LANG")
    if not lang:
        return cards
    import json
    words = json.load(open(os.path.join(HERE, "cards", f"{lang}.json")))["cards"]
    if len(words) != len(cards):
        sys.exit(f"cards/{lang}.json has {len(words)} cards, the film {len(cards)}")
    # thousands with a no-break space, as most of Europe writes them
    fill = {k: f"{v:,}".replace(",", "\u00a0") if isinstance(v, int) else v
            for k, v in shots.stats().items()}
    return [(t0, t1, layout, big.format(**fill), small.format(**fill))
            for (t0, t1, layout, _, _), (big, small) in zip(cards, words)]


def main():
    w, h, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    lines = []
    for i, (t0, t1, layout, big, small) in enumerate(translated(CARDS)):
        path = f"{out}/card_{i:02d}.png"
        card(w, h, layout, big, small).save(path)
        lines.append(f"{path} {t0} {t1 - t0:g} {t1 - t0 - 0.9:g}")
    open(f"{out}/cards.txt", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
