"""
Render the learning on the real Chennai map. For a given trip, draw the route the car drove
correctly (green) up to its first wrong turn (red = where it got lost), with the rest of the
true route faint grey — or the full green route when it ARRIVES. OSM tiles via staticmap.
"""
import json
import os
import time

from PIL import ImageDraw, ImageFont
from staticmap import StaticMap, Line, CircleMarker

from nav_tasks import DECISIONS, START, GOAL

HERE = os.path.dirname(os.path.abspath(__file__))
GEOM = [(lon, lat) for lon, lat in json.load(open(f"{HERE}/nav/route.json"))["routes"][0]["geometry"]["coordinates"]]
TILES = "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"
W, H = 980, 680


def _nearest_idx(loc):
    lon, lat = loc
    return min(range(len(GEOM)), key=lambda i: (GEOM[i][0] - lon) ** 2 + (GEOM[i][1] - lat) ** 2)


def render(trip, round_no, path):
    m = StaticMap(W, H, url_template=TILES, padding_x=70, padding_y=70)
    # faint full route (the correct way)
    m.add_line(Line(GEOM, "#b0b0b0", 3))
    reached = trip["reached"]
    fail = trip["first_fail"]
    cut = len(GEOM) if reached else _nearest_idx(DECISIONS[fail]["loc"]) + 1
    if cut > 1:                                            # the part driven correctly
        m.add_line(Line(GEOM[:cut], "#1fa971", 7))
    m.add_marker(CircleMarker((START[1], START[0]), "#2660ff", 15))   # station
    m.add_marker(CircleMarker((GOAL[1], GOAL[0]), "#1fa971" if reached else "#7a7a7a", 15))  # Jains Antariksha
    if not reached:
        m.add_marker(CircleMarker(tuple(DECISIONS[fail]["loc"]), "#e53935", 16))  # where it got lost

    img = m.render()
    d = ImageDraw.Draw(img)
    try:
        big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
        sm = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
    except Exception:
        big = sm = ImageFont.load_default()
    d.rectangle([0, 0, W, 72], fill=(12, 16, 22))
    status = "ARRIVED at Jains Antariksha" if reached else f"LOST — wrong turn at {DECISIONS[fail]['on']}"
    col = (73, 224, 139) if reached else (229, 83, 53)
    d.text((16, 10), f"Trip {round_no}", font=big, fill=(255, 255, 255))
    d.text((16, 44), f"{trip['correct_turns']}/{len(DECISIONS)} turns correct", font=sm, fill=(170, 170, 170))
    d.text((230, 22), status, font=big, fill=col)
    d.text((16, H - 26), "Kodambakkam station → Jains Antariksha  ·  route from OpenStreetMap",
           font=sm, fill=(90, 90, 90))
    img.save(path)
    print("wrote", path)


def build_video(frames):
    """Stitch the per-trip PNGs into a shareable MP4 + GIF with ffmpeg (hold on the arrival)."""
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found — skipping video"); return
    listing = f"{HERE}/out/frames/frames.txt"
    with open(listing, "w") as f:
        for i, fr in enumerate(frames):
            f.write(f"file '{os.path.basename(fr)}'\n")
            f.write(f"duration {3.0 if i == len(frames) - 1 else 1.6}\n")
        f.write(f"file '{os.path.basename(frames[-1])}'\n")       # concat needs the last frame twice
    mp4 = f"{HERE}/out/learning.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "frames.txt",
                    "-vf", "scale=980:680,format=yuv420p", "-r", "25", "learning.mp4"],
                   cwd=f"{HERE}/out/frames", check=True, capture_output=True)
    os.replace(f"{HERE}/out/frames/learning.mp4", mp4)
    gif = f"{HERE}/out/learning.gif"
    subprocess.run(["ffmpeg", "-y", "-i", mp4, "-vf",
                    "fps=12,scale=760:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                    gif], check=True, capture_output=True)
    print("wrote", mp4, "and", gif)


def main():
    hist = json.load(open(f"{HERE}/out/history.json"))["mnemo"]
    os.makedirs(f"{HERE}/out/frames", exist_ok=True)
    frames = []
    for p, trip in enumerate(hist):                              # every trip → one video frame
        fr = f"{HERE}/out/frames/frame_{p+1:02d}.png"
        render(trip, p + 1, fr)
        frames.append(fr)
        time.sleep(1.0)                                          # be polite to the OSM tile server
    # stills for the README: first trip, a mid trip, and the first arrival
    arrive = next((i for i, t in enumerate(hist) if t["reached"]), len(hist) - 1)
    for p in sorted({0, min(2, len(hist) - 1), arrive}):
        render(hist[p], p + 1, f"{HERE}/out/trip_{p+1:02d}.png")
    build_video(frames)


if __name__ == "__main__":
    main()
