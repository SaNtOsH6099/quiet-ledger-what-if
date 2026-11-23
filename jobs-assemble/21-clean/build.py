#!/usr/bin/env python3
"""Build Short 21 — "What If Chopsticks Never Existed?"
Adapted from build_21.py (short-16-two-suns) + build_13.py cards.

- Narration: narration-dominic-21a-norm.wav (38.34s, 48kHz).
  Rides are ALREADY in the mix (mix-21a.py): "eat," +2.0 dB,
  "Japan," +2.0 dB, "knife." +2.0 dB. Norm is STATIC gain + limiter,
  NOT loudnorm dynamic: aresample=48000,volume=+1.20dB,
  alimiter=limit=0.80:level=0 -> measured -16.42 LUFS, TP -1.89 dBTP
  on the norm file (+0.77dB gave -16.80; +1.20dB chosen, 89 samples at
  the 0.80 cap). Rides re-verified on the norm file (Short 13 lesson):
  eat 0.221->0.294, japan 0.458->0.528, knife 0.346->0.398.
- Items (video-time starts, 15 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 2.26, 02a 4.84, 02b 7.46, 03a 9.56, 03b 12.06,
  04a 15.54, 04b 17.98, 04c 21.12, 05a 23.38, 05b 25.62, 06a 28.12,
  06b 31.02, 06c 33.58, 07a 35.70. Video end 38.34.
  On-screen text cards (8, from stills-plan.md, drawtext per build_13.py,
  y=1600 below the caption band, on BOTH cuts):
  02a "1.5 billion people eat with chopsticks daily",
  03a "Earliest bronze chopsticks — Yin, Henan, ~1200 BC",
  04a "1200 BC → AD 400",
  04c "chopped small = less fuel, faster cooking",
  05b "Confucius: no knives at the table",
  06a "By AD 500: Vietnam → Korea → Japan",
  06b "chop = quick (Pidgin English)",
  06c "first written 1699".
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-21.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-21.ass (20 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "1200"/"1600"/"400"/"500"/"1699"
  merged tokens). ONE sync note: s1c12 "population" sweep starts 0.15s
  after onset (kf floors on coarticulated "when"+"a" eat 0.20s) — at the
  BAR, flagged for the captions chair, not a generator fail.

Modes:
  python3 build_21.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_21.py full
      -> full captioned render (35.34s)
  python3 build_21.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 38.34
NARR_NORM = "narration-dominic-21a-norm.wav"
ASS = "captions-21.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-21-01a", 0, "21-01a"),
    (2.26,  "frames-21-01b", 0, "21-01b"),
    (4.84,  "frames-21-02a", 0, "21-02a"),
    (7.46,  "frames-21-02b", 0, "21-02b"),
    (9.56,  "frames-21-03a", 0, "21-03a"),
    (12.06, "frames-21-03b", 0, "21-03b"),
    (15.54, "frames-21-04a", 0, "21-04a"),
    (17.98, "frames-21-04b", 0, "21-04b"),
    (21.12, "frames-21-04c", 0, "21-04c"),
    (23.38, "frames-21-05a", 0, "21-05a"),
    (25.62, "frames-21-05b", 0, "21-05b"),
    (28.12, "frames-21-06a", 0, "21-06a"),
    (31.02, "frames-21-06b", 0, "21-06b"),
    (33.58, "frames-21-06c", 0, "21-06c"),
    (35.70, "frames-21-07a", 0, "21-07a"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
CARDS = [
    (5.00, 7.30, "card-02a"),
    (9.80, 11.90, "card-03a"),
    (15.80, 17.80, "card-04a"),
    (21.30, 23.20, "card-04c"),
    (25.80, 27.90, "card-05b"),
    (28.30, 30.90, "card-06a"),
    (31.20, 33.40, "card-06b"),
    (33.80, 35.50, "card-06c"),
]
CARD_TEXT = {
    "card-02a": "1.5 billion people eat with chopsticks daily",
    "card-03a": "Earliest bronze chopsticks \u2014 Yin, Henan, ~1200 BC",
    "card-04a": "1200 BC \u2192 AD 400",
    "card-04c": "chopped small = less fuel, faster cooking",
    "card-05b": "Confucius: no knives at the table",
    "card-06a": "By AD 500: Vietnam \u2192 Korea \u2192 Japan",
    "card-06b": "chop = quick (Pidgin English)",
    "card-06c": "first written 1699",
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
                 f"x=(w-text_w)/2:y=1600:"
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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-21.json")))
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
    ap.add_argument("mode", choices=["test", "full", "clean"])
    ap.add_argument("--item", type=int, default=0)
    ap.add_argument("--at", type=float, default=1.0)
    args = ap.parse_args()

    if args.mode == "test":
        ass_path = os.path.join(BASE, ASS)
        assert os.path.exists(ass_path)
        shift = ITEMS[args.item][0]
        shifted = os.path.join(BASE, f"captions-test-21-shifted-item{args.item}.ass")
        txt = open(ass_path).read()

        def parse(t):
            h, mi, s = t.split(":")
            return int(h) * 3600 + int(mi) * 60 + float(s)

        out_lines = []
        for line in txt.splitlines():
            m = re.match(r"(Dialogue: 0,)(\d+:\d\d:\d\d\.\d\d),(\d+:\d\d:\d\d\.\d\d),(.*)$", line)
            if not m:
                out_lines.append(line)
                continue
            ne = parse(m.group(3)) - shift
            if ne <= 0:
                continue
            ns = max(0.0, parse(m.group(2)) - shift)
            out_lines.append(f"{m.group(1)}{ass_time(ns)},{ass_time(ne)},{m.group(4)}")
        open(shifted, "w").write("\n".join(out_lines) + "\n")
        st, d, sn, key = ITEMS[args.item]
        vf = [f"[0:v]format=yuv420p,settb=AVTB[v0]"]
        vf.append(f"[v0]subtitles='{shifted}'[vout]")
        out = os.path.join(BASE, f"test-clip-21-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-21-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("21 - What If Chopsticks Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("21 - What If Chopsticks Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
