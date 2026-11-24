#!/usr/bin/env python3
"""Build Short 26 — "What If Toothpicks Never Existed?"
Adapted from build_21.py (short-20-chopsticks) + build_13.py cards.

- Narration: narration-dominic-26a-norm.wav (48.16s, 48kHz).
  Rides are ALREADY in the mix (mix-26a.py): "habit," +3.0 dB,
  "sweets," +3.0 dB. Norm is STATIC gain + limiter:
  aresample=48000,volume=+1.74dB, alimiter=limit=0.80:level=0 ->
  measured -16.12 LUFS, TP -1.92 dBTP on the norm file (118 samples at
  the 0.80 cap — brief hook transients only). Rides re-verified on the
  norm file (Short 13 lesson): habit peak 0.530 -> 0.655,
  sweets peak 0.350 -> 0.428 (x1.221 = +1.74dB, as expected).
- Items (video-time starts, 18 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 2.50, 02a 5.84, 02b 8.44, 03a 11.58, 04a 13.38,
  04b 15.70, 04c 17.60, 05a 20.28, 05b 22.10, 06a 24.90, 06b 27.60,
  06c 30.60, 07a 34.06, 07b 36.80, 08a 39.64, 08b 42.40, 08c 45.40.
  Video end 48.16.
  On-screen text cards (5, from stills-plan.md, drawtext per build_13.py,
  y=1600 below the caption band, on BOTH cuts):
  02a "Strong, Maine — the Toothpick Capital of the World",
  02b "75 billion toothpicks a year, from a town of 1,000 people — after WWII"
      (two lines — 70 chars will not fit one line at 36px),
  04a "El Sidrón, Spain — 49,000 years ago",
  07a "1869 — one minute of machine work = one day of whittling"
      (two lines — 58 chars will not fit one line at 36px),
  08a "Last Maine toothpick factory closed, 2003".
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-26.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-26.ass (24 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "1,000"/"75"/"49,000" x2/"1500s"/"1869").
  ZERO sync notes (all sweeps within 0.15s of RMS spans, no sweep >0.15s
  through silence). Digit tokens verified against spans-26a.json by
  reading the ASS lines: "1,000" kf54 (6.97-7.52), "75" kf26 (9.66-9.92),
  "49,000" kf65 (15.29-15.94) and kf117 (44.05-45.22), "1500s" kf96,
  "1869," kf103 (ends 35.17 = voice-end).

Modes (run ONLY on the GitHub farm — never locally):
  python3 build_26.py full
      -> full captioned render (48.16s)
  python3 build_26.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 48.16
NARR_NORM = "narration-dominic-26a-norm.wav"
ASS = "captions-26.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-26-01a", 0, "26-01a"),
    (2.50,  "frames-26-01b", 0, "26-01b"),
    (5.84,  "frames-26-02a", 0, "26-02a"),
    (8.44,  "frames-26-02b", 0, "26-02b"),
    (11.58, "frames-26-03a", 0, "26-03a"),
    (13.38, "frames-26-04a", 0, "26-04a"),
    (15.70, "frames-26-04b", 0, "26-04b"),
    (17.60, "frames-26-04c", 0, "26-04c"),
    (20.28, "frames-26-05a", 0, "26-05a"),
    (22.10, "frames-26-05b", 0, "26-05b"),
    (24.90, "frames-26-06a", 0, "26-06a"),
    (27.60, "frames-26-06b", 0, "26-06b"),
    (30.60, "frames-26-06c", 0, "26-06c"),
    (34.06, "frames-26-07a", 0, "26-07a"),
    (36.80, "frames-26-07b", 0, "26-07b"),
    (39.64, "frames-26-08a", 0, "26-08a"),
    (42.40, "frames-26-08b", 0, "26-08b"),
    (45.40, "frames-26-08c", 0, "26-08c"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
CARDS = [
    (6.00, 8.30, "card-02a"),
    (8.60, 10.90, "card-02b"),
    (13.60, 15.50, "card-04a"),
    (34.30, 36.60, "card-07a"),
    (39.90, 42.20, "card-08a"),
]
CARD_TEXT = {
    "card-02a": "Strong, Maine \u2014 the Toothpick Capital of the World",
    "card-02b": "75 billion toothpicks a year,\nfrom a town of 1,000 people \u2014 after WWII",
    "card-04a": "El Sidr\u00f3n, Spain \u2014 49,000 years ago",
    "card-07a": "1869 \u2014 one minute of machine work\n= one day of whittling",
    "card-08a": "Last Maine toothpick factory closed, 2003",
}
# y position per card (two-line cards sit higher so the block stays in place)
CARD_Y = {
    "card-02a": 1600,
    "card-02b": 1560,
    "card-04a": 1600,
    "card-07a": 1560,
    "card-08a": 1600,
}


def write_cards():
    d = os.path.join(BASE, "cards")
    os.makedirs(d, exist_ok=True)
    for cid, text in CARD_TEXT.items():
        p = os.path.join(d, cid + ".txt")
        open(p, "w").write(text + "\n")
    return d


def card_filter(inp, out, card_dir):
    """Append the drawtext card filters to the chain. Returns final label."""
    cur = inp
    for i, (st, en, cid) in enumerate(CARDS):
        nxt = f"card{i}" if i < len(CARDS) - 1 else out
        tf = os.path.join(card_dir, cid + ".txt")
        cur_f = (f"[{cur}]drawtext=fontfile={FONT}:textfile={tf}:"
                 f"fontsize=36:fontcolor=white:borderw=2:bordercolor=black:"
                 f"x=(w-text_w)/2:y={CARD_Y[cid]}:"
                 f"enable='between(t,{st},{en})'[{nxt}]")
        cur = nxt
        yield cur_f


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def item_pad(i):
    """Hold-last-frame pad (seconds) so item i lasts until the next item's
    start + XFADE (the transition needs BOTH inputs through its end).
    The capture gives each item span*30+10 frames, but the
    sentence-boundary silences leave gaps — without the pad the xfade
    chain truncates at the first short item (16 v1 build: video ended
    at 7.73s, where item 03's frames ran out). The gap is a narration
    silence, so holding the last frame is the natural visual."""
    import json
    man = json.load(open(os.path.join(BASE, "cfg-manifest-26.json")))
    st, d, sn, key = ITEMS[i]
    nframes = man[key]["frames"]
    have = nframes / FPS
    end = ITEMS[i + 1][0] + XFADE if i + 1 < len(ITEMS) else NARR_END
    need = end - st
    return max(0.0, need - have)


def build_filtergraph(ass_path=None):
    filters = []
    for i, (st, d, sn, key) in enumerate(ITEMS):
        pad = item_pad(i)
        tpad = f",tpad=stop_duration={pad:.3f}" if pad > 0 else ""
        filters.append(f"[{i}:v]format=yuv420p,settb=AVTB{tpad}[v{i}]")
    prev = "v0"
    for i in range(1, len(ITEMS)):
        off = ITEMS[i][0]
        out = f"x{i}" if i < len(ITEMS) - 1 else "vpre"
        filters.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={off}[{out}]")
        prev = out
    # on-screen text cards (both cuts)
    card_dir = write_cards()
    filters.extend(card_filter(prev, "vcard", card_dir))
    prev = "vcard"
    if ass_path:
        filters.append(f"[{prev}]subtitles='{ass_path}'[vout]")
    else:
        filters.append(f"[{prev}]null[vout]")
    return ";".join(filters)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:], file=sys.stderr)
        sys.exit(1)
    return r


def render(out_name, ass_path):
    norm = os.path.join(BASE, NARR_NORM)
    assert os.path.exists(norm), f"missing {norm}"
    if ass_path:
        assert os.path.exists(ass_path), f"missing {ass_path}"
    fg = build_filtergraph(ass_path)
    onscreen = []
    for i in range(len(ITEMS)):
        end = ITEMS[i + 1][0] if i + 1 < len(ITEMS) else NARR_END
        onscreen.append(end - ITEMS[i][0])
    print(f"{len(ITEMS)} items, max on-screen {max(onscreen):.2f}s, total {NARR_END}s")
    for i in range(len(ITEMS)):
        print(f"  pad {ITEMS[i][3]}: {item_pad(i):.3f}s")
    out = os.path.join(BASE, out_name)
    cmd = ["ffmpeg", "-y"]
    for st, d, sn, key in ITEMS:
        cmd += ["-framerate", str(FPS), "-start_number", str(sn),
                "-i", os.path.join(BASE, d, "p_%03d.png")]
    cmd += ["-i", norm]
    cmd += ["-filter_complex", fg,
            "-map", "[vout]", "-map", f"{len(ITEMS)}:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-t", str(NARR_END),
            "-crf", "19", "-movflags", "+faststart", out]
    run(cmd)
    print(f"Done: {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["full", "clean"])
    args = ap.parse_args()

    if args.mode == "full":
        render("26 - What If Toothpicks Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("26 - What If Toothpicks Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
