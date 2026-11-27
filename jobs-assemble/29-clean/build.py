#!/usr/bin/env python3
"""Build Short 29 — "What If Forks Never Existed?"
Adapted from build_27.py (short-26-bobby-pins).

- Narration: narration-dominic-29a-norm.wav (51.52s, 48kHz).
  Rides are ALREADY in the mix (mix-29a.py): S5 tilt +1.5,
  S6 tilt +1.0 dB. Norm is STATIC gain + limiter, NOT loudnorm
  dynamic: aresample=48000, alimiter=limit=0.82:level=0 (no
  volume gain — the mix already measured -16.22 LUFS) ->
  measured -16.28 LUFS, TP -1.68 dBTP on the norm file
  (mix measured -16.22 / -0.40). Rides re-verified on the
  norm file: S5 +1.43 dB, S6 +0.96 dB vs the trim; S1-S4
  unchanged (-0.02 to -0.05 dB). Norm peak 0.821 (the 0.82 cap).
- Items (video-time starts, 20 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 2.76, 02a 4.96, 02b 7.60, 02c 8.94,
  03a 11.08, 03b 13.58, 03c 15.82, 03d 17.62, 03e 20.94,
  03f 24.18, 04a 26.98, 04b 28.64, 04c 30.98, 04d 33.96,
  05a 37.08, 05b 39.86, 05c 43.14, 06a 46.90, 06b 49.20.
  Video end 51.52.
  On-screen text cards (3, from stills-plan.md, drawtext per build_13.py,
  y=1600 below the caption band, on BOTH cuts):
  03a "Venice, 1004", 04a "Venice, 1006", 05c "Italy, 1400s".
  All one line (short texts, ~250px at 36px).
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-29.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-29.ass (28 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "2 years later," / "400" / "1004," /
  "15th"). Zero sync notes from the generator.

Modes:
  python3 build_29.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_29.py full
      -> full captioned render (51.52s)
  python3 build_29.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 51.52
NARR_NORM = "narration-dominic-29a-norm.wav"
ASS = "captions-29.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-29-01a", 0, "29-01a"),
    (2.76,  "frames-29-01b", 0, "29-01b"),
    (4.96,  "frames-29-02a", 0, "29-02a"),
    (7.60,  "frames-29-02b", 0, "29-02b"),
    (8.94,  "frames-29-02c", 0, "29-02c"),
    (11.08, "frames-29-03a", 0, "29-03a"),
    (13.58, "frames-29-03b", 0, "29-03b"),
    (15.82, "frames-29-03c", 0, "29-03c"),
    (17.62, "frames-29-03d", 0, "29-03d"),
    (20.94, "frames-29-03e", 0, "29-03e"),
    (24.18, "frames-29-03f", 0, "29-03f"),
    (26.98, "frames-29-04a", 0, "29-04a"),
    (28.64, "frames-29-04b", 0, "29-04b"),
    (30.98, "frames-29-04c", 0, "29-04c"),
    (33.96, "frames-29-04d", 0, "29-04d"),
    (37.08, "frames-29-05a", 0, "29-05a"),
    (39.86, "frames-29-05b", 0, "29-05b"),
    (43.14, "frames-29-05c", 0, "29-05c"),
    (46.90, "frames-29-06a", 0, "29-06a"),
    (49.20, "frames-29-06b", 0, "29-06b"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
# Windows sit inside their scene's beat; Kirby card at the 02c beat.
CARDS = [
    (11.30, 13.40, "card-03a"),
    (27.20, 28.50, "card-04a"),
    (43.40, 46.00, "card-05c"),
]
CARD_TEXT = {
    "card-03a": ["Venice, 1004"],
    "card-04a": ["Venice, 1006"],
    "card-05c": ["Italy, 1400s"],
}


def write_cards():
    d = os.path.join(BASE, "cards")
    os.makedirs(d, exist_ok=True)
    for cid, lines in CARD_TEXT.items():
        for li, text in enumerate(lines):
            p = os.path.join(d, f"{cid}-{li}.txt")
            open(p, "w").write(text + "\n")
    return d


def card_filter(inp, out, card_dir):
    """Append the drawtext card filters to the chain. Returns final label.
    Each card line gets its OWN drawtext (y=1600 + 45*line) — a newline
    inside one textfile renders a tofu box at the end of the line, so
    multi-line cards are never one textfile (v1 defect, fixed here)."""
    cur = inp
    filters = []
    for i, (st, en, cid) in enumerate(CARDS):
        for li in range(len(CARD_TEXT[cid])):
            is_last = (i == len(CARDS) - 1 and li == len(CARD_TEXT[cid]) - 1)
            nxt = out if is_last else f"card{i}_{li}"
            tf = os.path.join(card_dir, f"{cid}-{li}.txt")
            y = 1600 + 45 * li
            filters.append(
                f"[{cur}]drawtext=fontfile={FONT}:textfile={tf}:"
                f"fontsize=36:fontcolor=white:borderw=2:bordercolor=black:"
                f"x=(w-text_w)/2:y={y}:"
                f"enable='between(t,{st},{en})'[{nxt}]")
            cur = nxt
    return filters


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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-29.json")))
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
        # BLACK frames for the pad — 26's v2 shipped 7 black holes from this;
        # 27's v2 shipped 4 (7.5s, 22.4s, 38.3s, 47.6s). Clone holds the
        # last frame through the pad instead.
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
        shifted = os.path.join(BASE, f"captions-test-29-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-29-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-29-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("29 - What If Forks Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("29 - What If Forks Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
