#!/usr/bin/env python3
"""Build Short 25 — "What If Paper Clips Never Existed?"
Adapted from build_21.py (short-20-chopsticks) + build_13.py cards.

- Narration: narration-dominic-25d-norm.wav (43.37s, 48kHz).
  Rides are ALREADY in the mix (mix-25d.py): "stuck" +3.0 dB,
  "honor." +2.0 dB, "together." +3.0 dB, all 20ms feather, verified on
  the norm file. Norm is STATIC gain + limiter, NOT loudnorm dynamic:
  aresample=48000,volume=+1.70dB,
  alimiter=limit=0.80:level=0 -> measured -16.3 LUFS, TP -1.9 dBTP
  on the norm file.
- Items (video-time starts, 16 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 3.00, 02a 6.10, 02b 9.41, 02c 12.36, 03a 15.24,
  03b 17.43, 03c 20.01, 03d 22.47, 04a 24.61, 04b 27.93, 04c 30.01,
  04d 31.69, 04e 33.23, 05a 35.36, 05b 39.39. Video end 43.37.
  On-screen text cards (7, from stills-plan.md, drawtext per build_13.py,
  y=1600 below the caption band, on BOTH cuts):
  02b "Samuel B. Fay — US patent 1867",
  03b "The Gem — never patented, Britain, 1870s",
  03c "Johan Vaaler — German patent 1900, US patent 1901",
  04a "King Haakon VII — his initials on the badges",
  04c "Norway, WWII — paper clips on lapels",
  05a "Sandvika, 1989 — a 23-foot paper clip" (before the 37.9s reframe),
  05a "The statue is a Gem — not Vaaler's design" (after the reframe).
  Card texts shortened from the plan where the full text would overflow
  1080px at 36px (03b drops "one and a half loops", 04a drops "the
  banned", 04c drops the quote — all three facts are carried by the
  narration + captions anyway). Widths measured with PIL: max 965px.
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-25.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-25.ass (26 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "1867"/"1989"/"23-foot" merged
  tokens; "vaaler's" lowercase per the 15/16/21 display convention).
  KNOWN FLAW (waived, 25d continuity): "before" (S2) was never voiced;
  its caption word sweeps at the next word's onset (~6.5s) — the word
  is in the script and stays in the captions, the sweep lands ~0.6s
  before "the clip" is spoken. Flagged for the captions chair.
- 05b uses a NEGATIVE farm zoom (-0.012): the close on the wire eases
  out to the wide map reveal (the plan's 41.5s reframe, rendered
  natively, verified zoom-final MAD 2.04 at Gate 4).

Modes:
  python3 build_25.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_25.py full
      -> full captioned render (43.37s)
  python3 build_25.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 43.37
NARR_NORM = "narration-dominic-25d-norm.wav"
ASS = "captions-25.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-25-01a", 0, "25-01a"),
    (3.00,  "frames-25-01b", 0, "25-01b"),
    (6.10,  "frames-25-02a", 0, "25-02a"),
    (9.41,  "frames-25-02b", 0, "25-02b"),
    (12.36, "frames-25-02c", 0, "25-02c"),
    (15.24, "frames-25-03a", 0, "25-03a"),
    (17.43, "frames-25-03b", 0, "25-03b"),
    (20.01, "frames-25-03c", 0, "25-03c"),
    (22.47, "frames-25-03d", 0, "25-03d"),
    (24.61, "frames-25-04a", 0, "25-04a"),
    (27.93, "frames-25-04b", 0, "25-04b"),
    (30.01, "frames-25-04c", 0, "25-04c"),
    (31.69, "frames-25-04d", 0, "25-04d"),
    (33.23, "frames-25-04e", 0, "25-04e"),
    (35.36, "frames-25-05a", 0, "25-05a"),
    (39.39, "frames-25-05b", 0, "25-05b"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
CARDS = [
    (9.60, 12.10, "card-02b"),
    (17.60, 19.80, "card-03b"),
    (20.20, 22.20, "card-03c"),
    (25.00, 27.70, "card-04a"),
    (30.10, 31.60, "card-04c"),
    (35.60, 37.70, "card-05a-1"),
    (37.90, 39.30, "card-05a-2"),
]
CARD_TEXT = {
    "card-02b": "Samuel B. Fay — US patent 1867",
    "card-03b": "The Gem — never patented, Britain, 1870s",
    "card-03c": "Johan Vaaler — German patent 1900, US patent 1901",
    "card-04a": "King Haakon VII — his initials on the badges",
    "card-04c": "Norway, WWII — paper clips on lapels",
    "card-05a-1": "Sandvika, 1989 — a 23-foot paper clip",
    "card-05a-2": "The statue is a Gem — not Vaaler's design",
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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-25.json")))
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
        shifted = os.path.join(BASE, f"captions-test-25-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-25-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-25-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("25 - What If Paper Clips Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("25 - What If Paper Clips Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
