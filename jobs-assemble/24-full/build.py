#!/usr/bin/env python3
"""Build Short 24 — "What If Shoelaces Never Existed?"
Adapted from build_21.py (short-20-chopsticks).

- Narration: narration-dominic-24a-norm.wav (39.93s, 48kHz).
  Rides are ALREADY in the mix (mix-24a.py): "your knot" +2.0 dB,
  "free," +2.0 dB, "time." +2.0 dB. Norm is STATIC gain + limiter,
  NOT loudnorm dynamic: aresample=48000,volume=+1.80dB,
  alimiter=limit=0.80:level=0 -> measured -16.39 LUFS, TP -1.89 dBTP
  on the norm file (mix measured -18.05 LUFS, TP -1.16; 79 samples at
  the 0.80 cap). Rides re-verified on the norm file (Short 13 lesson):
  your knot 0.607->0.746, free 0.401->0.494, time 0.324->0.402
  (exactly the +1.80 dB static gain — the limiter never touched them).
- Items (video-time starts, 15 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 3.18, 02a 5.48, 02b 8.32, 03a 11.68, 03b 14.76,
  03c 17.66, 04a 20.34, 04b 22.22, 04c 25.46, 05a 28.14, 05b 30.98,
  05c 32.66, 06a 35.42, 06b 37.90. Video end 39.93.
  On-screen text cards (7, from stills-plan.md + script-v2.md, drawtext
  per build_13.py, y=1600 below the caption band, on BOTH cuts):
  02a "oldest known leather shoe — Areni-1, Armenia, ~3500 BC"
  03a "Harvey Kennedy — aglet patent, 27 March 1790"
  03b "aglet — from Latin/French for 'needle'"
  03c "buckles were the expensive alternative"
  04b "Berkeley, 2017 — footfall ~7x gravity"
  05a "1941: burrs on a walk with his dog"
  05b "1955: Velcro patent (velours + crochet)"
  Card texts are the plan's wording condensed to fit one 36px line
  (measured with PIL: 622-1043px of 1080px — the 02a card is kept full
  at 1043px; the others drop a clause the narration already speaks).
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-24.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-24.ass (21 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "5,500"/"1790,"/"2017,"/"1955,"
  merged tokens, single \\kf per token as in 21). Zero sync notes.

Modes:
  python3 build_24.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S. (FARM ONLY — do not run locally.)
  python3 build_24.py full
      -> full captioned render (39.93s)
  python3 build_24.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 39.93
NARR_NORM = "narration-dominic-24a-norm.wav"
ASS = "captions-24.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-24-01a", 0, "24-01a"),
    (3.18,  "frames-24-01b", 0, "24-01b"),
    (5.48,  "frames-24-02a", 0, "24-02a"),
    (8.32,  "frames-24-02b", 0, "24-02b"),
    (11.68, "frames-24-03a", 0, "24-03a"),
    (14.76, "frames-24-03b", 0, "24-03b"),
    (17.66, "frames-24-03c", 0, "24-03c"),
    (20.34, "frames-24-04a", 0, "24-04a"),
    (22.22, "frames-24-04b", 0, "24-04b"),
    (25.46, "frames-24-04c", 0, "24-04c"),
    (28.14, "frames-24-05a", 0, "24-05a"),
    (30.98, "frames-24-05b", 0, "24-05b"),
    (32.66, "frames-24-05c", 0, "24-05c"),
    (35.42, "frames-24-06a", 0, "24-06a"),
    (37.90, "frames-24-06b", 0, "24-06b"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
CARDS = [
    (5.68, 8.12, "card-02a"),
    (11.88, 14.56, "card-03a"),
    (14.96, 17.46, "card-03b"),
    (17.86, 20.14, "card-03c"),
    (22.42, 25.26, "card-04b"),
    (28.34, 30.78, "card-05a"),
    (31.18, 32.46, "card-05b"),
]
CARD_TEXT = {
    "card-02a": "oldest known leather shoe \u2014 Areni-1, Armenia, ~3500 BC",
    "card-03a": "Harvey Kennedy \u2014 aglet patent, 27 March 1790",
    "card-03b": "aglet \u2014 from Latin/French for 'needle'",
    "card-03c": "buckles were the expensive alternative",
    "card-04b": "Berkeley, 2017 \u2014 footfall ~7x gravity",
    "card-05a": "1941: burrs on a walk with his dog",
    "card-05b": "1955: Velcro patent (velours + crochet)",
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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-24.json")))
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
        tpad = f",tpad=stop_duration={pad:.3f}:stop_mode=clone" if pad > 0 else ""
        # stop_mode=clone is REQUIRED: tpad's default stop_mode=add appends
        # BLACK frames for the pad (26 v2: 7 holes, 27 v2: 4, 22 v1: 7).
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
        shifted = os.path.join(BASE, f"captions-test-24-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-24-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-24-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("24 - What If Shoelaces Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("24 - What If Shoelaces Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
