"""
Assemble a captioned pitch video from the real learning footage + title/curve/closing cards.
Output: ~/Desktop/RouteMind_Demo.mp4 (and docs/demo.mp4). Needs ffmpeg.
"""
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 980, 680
BG = (10, 13, 18)
MN, RG, ATLAS, BLUE, MUT, FG = (31, 201, 138), (228, 102, 31), (0, 199, 103), (37, 99, 235), (139, 149, 165), (234, 238, 244)
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONTB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
TMP = tempfile.mkdtemp(prefix="rmvid_")


def f(sz, bold=True):
    try:
        return ImageFont.truetype(FONTB if bold else FONT, sz)
    except Exception:
        return ImageFont.load_default()


def center(d, y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=fill)


def card(path, blocks, image=None):
    """blocks: list of (text, size, color, bold). Vertically centered stack."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # subtle top accent
    d.rectangle([0, 0, W, 5], fill=MN)
    heights = [sz + 16 for _, sz, _, _ in blocks]
    img_h = 0
    if image:
        im = Image.open(image).convert("RGB")
        scale = min(760 / im.width, 300 / im.height)
        im = im.resize((int(im.width * scale), int(im.height * scale)))
        img_h = im.height + 20
    total = sum(heights) + img_h
    y = (H - total) / 2
    if image:
        img.paste(im, (int((W - im.width) / 2), int(y)))
        y += im.height + 20
    for (text, sz, color, bold), hh in zip(blocks, heights):
        center(d, y, text, f(sz, bold), color)
        y += hh
    img.save(path)
    return path


def clip(png, dur, out):
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", png,
                    "-vf", f"scale={W}:{H},format=yuv420p,fade=t=in:d=0.3,fade=t=out:st={dur-0.3}:d=0.3",
                    "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
                   check=True, capture_output=True)
    return out


def main():
    cards = []
    cards.append(card(f"{TMP}/c1.png", [
        ("RouteMind", 80, FG, True),
        ("Agent memory that learns the route", 30, MUT, False),
        ("by forgetting its own wrong turns", 30, MUT, False),
        ("  ", 14, MUT, False),
        ("MongoDB Atlas Vector Search  ·  Voyage AI", 24, ATLAS, True),
    ]))
    cards.append(card(f"{TMP}/c2.png", [
        ("Shack 15  →  Ocean Beach", 44, FG, True),
        ("San Francisco, on real OpenStreetMap roads", 26, MUT, False),
        ("  ", 10, MUT, False),
        ("1,081 memories in Atlas. Most of them wrong.", 28, FG, False),
        ("Watch it learn the way.", 28, MN, True),
    ]))
    # learning footage inserted here
    curve = f"{HERE}/out/sf/curve.png"
    cards_curve = card(f"{TMP}/c3.png", [
        ("Arrives by trip 5.", 34, MN, True),
        ("Plain RAG, same memory frozen, never leaves the first block.", 24, MUT, False),
    ], image=curve if os.path.exists(curve) else None)
    cards.append(cards_curve)
    cards.append(card(f"{TMP}/c4.png", [
        ("Why vector search alone is not enough", 32, FG, True),
        ("  ", 10, MUT, False),
        ("At a junction, every candidate turn scores similarity 1.000.", 26, MUT, False),
        ("Similarity cannot tell the right turn from the wrong ones.", 26, MUT, False),
        ("  ", 10, MUT, False),
        ("Usefulness, learned and stored in Atlas, picks the turn.", 28, MN, True),
    ]))
    cards.append(card(f"{TMP}/c5.png", [
        ("It got lost in San Francisco,", 38, FG, True),
        ("then it learned the way.", 38, MN, True),
        ("  ", 14, MUT, False),
        ("MongoDB Atlas · Voyage AI · Raindrop · Modelence · ElevenLabs", 22, MUT, False),
        ("tets-mv4eiaze9dc-prod.cloud.modelence.app", 22, BLUE, True),
    ]))

    # build clips: title, setup, [learning], curve, money, outro
    segs = []
    segs.append(clip(cards[0], 4.0, f"{TMP}/s1.mp4"))
    segs.append(clip(cards[1], 3.2, f"{TMP}/s2.mp4"))
    learn = f"{HERE}/out/sf/learning.mp4"
    learn_norm = f"{TMP}/learn.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", learn, "-vf", f"scale={W}:{H},format=yuv420p",
                    "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", learn_norm],
                   check=True, capture_output=True)
    segs.append(learn_norm)
    segs.append(clip(cards[2], 4.5, f"{TMP}/s3.mp4"))
    segs.append(clip(cards[3], 5.5, f"{TMP}/s4.mp4"))
    segs.append(clip(cards[4], 4.5, f"{TMP}/s5.mp4"))

    listing = f"{TMP}/list.txt"
    with open(listing, "w") as fp:
        for s in segs:
            fp.write(f"file '{s}'\n")
    out = os.path.expanduser("~/Desktop/RouteMind_Demo.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listing,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                   check=True, capture_output=True)
    subprocess.run(["cp", out, f"{HERE}/docs/demo.mp4"], check=True)
    sz = os.path.getsize(out) // 1024
    print(f"wrote {out} ({sz} KB) and docs/demo.mp4")


if __name__ == "__main__":
    main()
