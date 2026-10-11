"""
Assemble a NARRATED, CAPTIONED pitch video for RouteMind.
Narration uses the Cutroom ElevenLabs narrator voice (from ~/workspace/cutroom/.env).
Visuals: title/stat/curve/closing cards + the real learning footage. Captions are burned
subtitles synced to the narration. Output: ~/Desktop/RouteMind_Demo.mp4 and docs/demo.mp4.
"""
import os
import subprocess
import tempfile
import urllib.request

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))                        # OPENAI_API_KEY
load_dotenv(os.path.expanduser("~/workspace/cutroom/.env"))    # Cutroom ElevenLabs (if valid)
EL_VOICE = os.environ.get("CUTROOM_ELEVEN_VOICE", "cjVigY5qzO86Huf0OWal")
W, H = 980, 680
BG = (10, 13, 18)
MN, RG, ATLAS, BLUE, MUT, FG = (31, 201, 138), (228, 102, 31), (0, 199, 103), (90, 150, 250), (150, 160, 176), (234, 238, 244)
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONTB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
TMP = tempfile.mkdtemp(prefix="rmvid_")


def ff(sz, bold=True):
    try:
        return ImageFont.truetype(FONTB if bold else FONT, sz)
    except Exception:
        return ImageFont.load_default()


def center(d, y, text, font, fill):
    d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)


def card(path, blocks, image=None):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 5], fill=MN)
    heights = [sz + 18 for _, sz, _, _ in blocks]
    img_h = 0
    im = None
    if image:
        im = Image.open(image).convert("RGB")
        s = min(720 / im.width, 300 / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        img_h = im.height + 24
    y = (H - (sum(heights) + img_h)) / 2 - 40        # lift a bit to leave room for captions
    if im:
        img.paste(im, (int((W - im.width) / 2), int(y))); y += im.height + 24
    for (text, sz, color, bold), hh in zip(blocks, heights):
        center(d, y, text, ff(sz, bold), color); y += hh
    img.save(path)
    return path


import json


def tts(text, path):
    el = os.environ.get("ROUTEMIND_ELEVEN_KEY")
    if el:                                                    # 1) ElevenLabs if a valid key is provided
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{EL_VOICE}",
            data=json.dumps({"text": text, "model_id": "eleven_turbo_v2_5",
                             "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}}).encode(),
            headers={"xi-api-key": el, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
        return path
    oa = os.environ.get("OPENAI_API_KEY")
    if oa:                                                    # 2) OpenAI TTS-HD (onyx), high quality
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps({"model": "tts-1-hd", "voice": os.environ.get("ROUTEMIND_TTS_VOICE", "onyx"),
                             "input": text, "response_format": "mp3", "speed": 1.0}).encode(),
            headers={"Authorization": f"Bearer {oa}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
        return path
    aiff = path.rsplit(".", 1)[0] + ".aiff"                   # 3) last resort: macOS system voice
    subprocess.run(["say", "-v", "Daniel", "-r", "178", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", aiff, path], check=True, capture_output=True)
    return path


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(out.stdout.strip())


def srt_ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


# scene = (card_blocks_or_"learn", narration+caption text, image)
SCENES = [
    # 1 - the problem
    ([("RouteMind", 78, FG, True)],
     "An agent is only as good as its memory. And today, that memory is frozen.", None),
    ([("Agent memory today is", 40, FG, True), ("frozen", 70, RG, True)],
     "It retrieves by similarity, and never learns from what happened next. So when a recall leads the agent wrong, nothing changes, and it makes the same mistake again, and again.", None),
    # 2 - what we built
    ([("A memory that", 40, FG, True), ("improves itself", 56, MN, True)],
     "We built RouteMind to fix that. A memory that improves itself. After every decision it scores whether the memory it recalled actually helped, keeps the useful ones, and deletes the ones that mislead. All of it on MongoDB Atlas Vector Search, with embeddings from Voyage AI.", None),
    # 3 - the key insight
    ([("similarity  1.000", 56, FG, True), ("  ", 8, FG, False),
      ("every candidate scores the same", 26, MUT, False),
      ("usefulness, learned in Atlas, picks the turn", 28, MN, True)],
     "Here is why this is hard. At a junction, every possible turn scores the same vector similarity. Similarity alone cannot tell the right turn from the wrong ones. The usefulness we learn and store in Atlas is what picks the turn.", None),
    # 4 - the demo setup
    ([("Shack 15  →  Ocean Beach", 48, FG, True), ("San Francisco", 28, MUT, False),
      ("  ", 10, FG, False), ("1,081 memories in Atlas, most of them wrong", 25, MN, True)],
     "To prove it, we gave it a real San Francisco drive, from Shack 15 to Ocean Beach, with over a thousand memories in Atlas, most of them wrong.", None),
    # 5 - the demo
    ("learn",
     "Now watch it learn. Each trip it recalls a turn, gets corrected, and forgets the turns that misled it, and the route locks in, trip by trip.", None),
    # 6 - the result
    ([("Arrives by trip 5", 42, MN, True)],
     "By trip five, it arrives. The same memory, with learning switched off, never leaves the first block.",
     f"{HERE}/out/sf/curve.png"),
    # 7 - close
    ([("Self-improving agent memory", 34, FG, True), ("  ", 8, FG, False),
      ("MongoDB Atlas · Voyage AI · Raindrop · Modelence · ElevenLabs", 20, MUT, False)],
     "RouteMind. Self-improving agent memory, on MongoDB Atlas and Voyage AI.", None),
]


def main():
    learn_src = f"{HERE}/out/sf/learning.mp4"
    learn_dur = dur(learn_src)
    scene_videos, srt, t0 = [], [], 0.0
    for i, (blocks, narr, image) in enumerate(SCENES):
        a = tts(narr, f"{TMP}/a{i}.mp3")
        ad = dur(a)
        sd = round(ad + 0.8, 2)                       # scene length = narration + tail
        # visual (silent), scaled to WxH
        vid = f"{TMP}/v{i}.mp4"
        if blocks == "learn":
            speed = learn_dur / sd
            subprocess.run(["ffmpeg", "-y", "-i", learn_src,
                            "-vf", f"setpts=PTS/{speed:.4f},scale={W}:{H},format=yuv420p",
                            "-an", "-r", "30", "-t", str(sd), "-c:v", "libx264", "-pix_fmt", "yuv420p", vid],
                           check=True, capture_output=True)
        else:
            png = card(f"{TMP}/c{i}.png", blocks, image=image)
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", str(sd), "-i", png,
                            "-vf", f"scale={W}:{H},format=yuv420p,fade=t=in:d=0.3,fade=t=out:st={sd-0.3}:d=0.3",
                            "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", vid], check=True, capture_output=True)
        # mux narration (delayed 250ms) onto the scene
        out = f"{TMP}/s{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", vid, "-i", a,
                        "-af", "adelay=250|250,apad", "-t", str(sd),
                        "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "160k", out],
                       check=True, capture_output=True)
        scene_videos.append(out)
        srt.append((t0 + 0.25, t0 + sd, narr)); t0 += sd

    # subtitles file
    srtp = f"{TMP}/cap.srt"
    with open(srtp, "w") as f:
        for n, (a, b, text) in enumerate(srt, 1):
            f.write(f"{n}\n{srt_ts(a)} --> {srt_ts(b)}\n{text}\n\n")

    # concat scenes
    lst = f"{TMP}/list.txt"
    with open(lst, "w") as f:
        for s in scene_videos:
            f.write(f"file '{s}'\n")
    concat = f"{TMP}/concat.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", concat],
                   check=True, capture_output=True)

    # burn captions
    out = os.path.expanduser("~/Desktop/RouteMind_Demo.mp4")
    style = ("FontName=Arial,FontSize=19,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=32,MarginL=70,MarginR=70")
    subprocess.run(["ffmpeg", "-y", "-i", concat,
                    "-vf", f"subtitles={srtp}:force_style='{style}'",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", out], check=True, capture_output=True)
    subprocess.run(["cp", out, f"{HERE}/docs/demo.mp4"], check=True)
    print(f"wrote {out} ({os.path.getsize(out)//1024} KB, {round(t0,1)}s, narrated + captioned) and docs/demo.mp4")


if __name__ == "__main__":
    main()
