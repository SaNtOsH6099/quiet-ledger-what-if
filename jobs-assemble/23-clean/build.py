"""Build Short 23 — "What If Belts Never Existed?"
Adapted from build_21.py (short-20-chopsticks).

- Narration: narration-dominic-23a-norm.wav (46.07s, 48kHz).
  NO rides (23a ships with none — assessment-dominic-23a.md). Norm is
  STATIC gain + limiter, NOT loudnorm dynamic: aresample=48000,
  volume=+1.40dB, alimiter=limit=0.80:level=0 -> measured -16.39 LUFS,
  TP -1.91 dBTP on the norm file.
- Items (video-time starts, 15 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 2.30, 02a 5.55, 02b 8.60, 03a 11.20, 03b 14.20,
  04a 18.54, 04b 21.80, 05a 24.26, 05b 28.20, 06a 32.84, 06b 35.60,
  07a 38.44, 07b 41.30, 07c 43.60. Video end 46.07.
  On-screen text cards (6 + 1 split line, from GATE1-LOCKED.md,
  drawtext, y=1600 below the caption band, on BOTH cuts):
  03a "Ötzi ~3300 BC",
  04a "Bronze Age buckles",
  04b "Cingulum — badge of rank",
  05a "Albert Thurston, London, 1822 — suspenders (braces)",
  06a "Levi's 501, 1922 — first belt loops",
  07a "Nils Bohlin, Volvo, 1959 — three-point seat belt" (y=1555) +
      "a million lives saved (Volvo estimate)" (y=1600).
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-23.json.
- Captions: captions-23.ass (21 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "5,000"/"3300"/"1822"/"100"/"1922"/
  "1959" merged tokens). No sync notes from the generator.

Modes:
  python3 build_23.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_23.py full
      -> full captioned render (46.07s)
  python3 build_23.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 46.07
NARR_NORM = "narration-dominic-23a-norm.wav"
ASS = "captions-23.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-23-01a", 0, "23-01a"),
    (2.30,  "frames-23-01b", 0, "23-01b"),
    (5.55,  "frames-23-02a", 0, "23-02a"),
    (8.60,  "frames-23-02b", 0, "23-02b"),
    (11.20, "frames-23-03a", 0, "23-03a"),
    (14.20, "frames-23-03b", 0, "23-03b"),
    (18.54, "frames-23-04a", 0, "23-04a"),
    (21.80, "frames-23-04b", 0, "23-04b"),
    (24.26, "frames-23-05a", 0, "23-05a"),
    (28.20, "frames-23-05b", 0, "23-05b"),
    (32.84, "frames-23-06a", 0, "23-06a"),
    (35.60, "frames-23-06b", 0, "23-06b"),
    (38.44, "frames-23-07a", 0, "23-07a"),
    (41.30, "frames-23-07b", 0, "23-07b"),
    (43.60, "frames-23-07c", 0, "23-07c"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
CARDS = [
    (11.40, 14.00, "card-03a", 1600),
    (18.80, 21.60, "card-04a", 1600),
    (22.00, 24.10, "card-04b", 1600),
    (24.50, 28.00, "card-05a", 1600),
    (33.00, 35.40, "card-06a", 1600),
    (38.70, 41.10, "card-07a", 1555),
    (38.70, 41.10, "card-07a2", 1600),
]
CARD_TEXT = {
    "card-03a": "\u00d6tzi ~3300 BC",
    "card-04a": "Bronze Age buckles",
    "card-04b": "Cingulum \u2014 badge of rank",
    "card-05a": "Albert Thurston, London, 1822 \u2014 suspenders (braces)",
    "card-06a": "Levi's 501, 1922 \u2014 first belt loops",
    "card-07a": "Nils Bohlin, Volvo, 1959 \u2014 three-point seat belt",
    "card-07a2": "a million lives saved (Volvo estimate)",
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
    for i, (st, en, cid, cy) in enumerate(CARDS):
        nxt = f"card{i}" if i < len(CARDS) - 1 else out
        tf = os.path.join(card_dir, cid + ".txt")
        cur_f = (f"[{cur}]drawtext=fontfile={FONT}:textfile={tf}:"
                 f"fontsize=36:fontcolor=white:borderw=2:bordercolor=black:"
                 f"x=(w-text_w)/2:y={cy}:"
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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-23.json")))
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
        shifted = os.path.join(BASE, f"captions-test-23-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-23-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-23-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("23 - What If Belts Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("23 - What If Belts Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
