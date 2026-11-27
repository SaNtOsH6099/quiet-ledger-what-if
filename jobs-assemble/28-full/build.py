#!/usr/bin/env python3
"""Build Short 28 — "What If Coat Hangers Never Existed?"
Adapted from build_27.py (short-26-bobby-pins).

- Narration: narration-dominic-28a-norm.wav (48.35s, 48kHz).
  Rides are ALREADY in the mix (mix-28a.py): S5 tilt +2.0 dB (26.28-30.04),
  "full" +1.5 (25.38-25.76), "Patterson" +1.5 (31.72-32.02), "penny" +2.0
  (39.88-40.16), "earth" +3.0 (47.72-48.00). Norm is STATIC gain + limiter,
  NOT loudnorm dynamic: aresample=48000,volume=+2.06dB,
  alimiter=limit=0.82:level=0 -> measured -16.11 LUFS, TP -1.69 dBTP
  on the norm file (mix measured -18.06 / -1.69). Rides re-verified
  on the norm file: deltas +1.40 to +2.26 dB over the mix vs control
  +2.12 dB (S5 slightly lower — limiter touched its loudest peaks).
- Items (video-time starts, 18 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 2.40, 01c 4.80, 02a 7.54, 02b 9.40, 03a 11.84,
  03b 14.40, 04a 17.82, 04b 20.40, 04c 23.20, 05a 26.28, 05b 28.20,
  06a 30.58, 06b 33.20, 06c 35.90, 07a 38.80, 07b 41.50, 07c 44.30.
  Video end 48.35. 07c is 3.70s — the farm zoom (0.015 push-in toward
  zoomCentre) is its second framing; no assembly-side crop (same as 27).
  On-screen text cards (5, from script-v3.md, drawtext per build_13.py,
  y=1600 below the caption band, on BOTH cuts):
  03a "O. A. North, New Britain, Connecticut — clothes hook, U.S. Patent 85,756, 12 January 1869",
  04a "Albert J. Parkhouse, Timberlake Wire and Novelty Co., Jackson, Michigan — 1903",
  06a "25 January 1904 — Charles L. Patterson files, naming himself inventor",
  06b "U.S. Patent 822,981, granted 1906, assigned to John B. Timberlake — then, an employee's invention belonged to the employer",
  07a "Parkhouse left for Los Angeles — his own wire company".
  Card widths measured with PIL at 36px (DejaVuSans): 03a 966/656px,
  04a 964/472px, 06a 813/440px, 06b 857/943/468px, 07a 1004px — all lines
  fit 1080px; 03a/04a/06a split into TWO lines, 06b into THREE, 07a one line.
  Cards land inside their scene's beat only; North card at 03a only (do NOT
  repeat at 03b), Parkhouse card at 04a only (do NOT repeat at 04b),
  patent card at 06b only (do NOT repeat at 06c), LA card at 07a only
  (do NOT repeat at 07b).
  v1 DEFECT (found at Gate 5 frame QC on 27, fixed in v2): a newline inside
  one drawtext textfile renders a TOFU BOX at the end of the first
  line (all four two-line cards) — the fix is one drawtext filter PER
  LINE (y=1600 + 45*line), never a newline inside a textfile.
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-28.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-28.ass (25 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "1869,"/"1903,"/"1906" merged tokens,
  "OA" initials). Zero sync notes from the generator.

Modes:
  python3 build_27.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_27.py full
      -> full captioned render (48.35s)
  python3 build_27.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 48.35
NARR_NORM = "narration-dominic-28a-norm.wav"
ASS = "captions-28.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-28-01a", 0, "28-01a"),
    (2.40,  "frames-28-01b", 0, "28-01b"),
    (4.80,  "frames-28-01c", 0, "28-01c"),
    (7.54,  "frames-28-02a", 0, "28-02a"),
    (9.40,  "frames-28-02b", 0, "28-02b"),
    (11.84, "frames-28-03a", 0, "28-03a"),
    (14.40, "frames-28-03b", 0, "28-03b"),
    (17.82, "frames-28-04a", 0, "28-04a"),
    (20.40, "frames-28-04b", 0, "28-04b"),
    (23.20, "frames-28-04c", 0, "28-04c"),
    (26.28, "frames-28-05a", 0, "28-05a"),
    (28.20, "frames-28-05b", 0, "28-05b"),
    (30.58, "frames-28-06a", 0, "28-06a"),
    (33.20, "frames-28-06b", 0, "28-06b"),
    (35.90, "frames-28-06c", 0, "28-06c"),
    (38.80, "frames-28-07a", 0, "28-07a"),
    (41.50, "frames-28-07b", 0, "28-07b"),
    (44.30, "frames-28-07c", 0, "28-07c"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
# Windows sit inside their scene's beat; Kirby card at the 02c beat.
CARDS = [
    (12.00, 14.30, "card-03a"),
    (18.00, 20.30, "card-04a"),
    (30.70, 33.10, "card-06a"),
    (33.30, 35.80, "card-06b"),
    (38.90, 41.40, "card-07a"),
]
CARD_TEXT = {
    "card-03a": ["O. A. North, New Britain, Connecticut \u2014 clothes hook,",
                 "U.S. Patent 85,756, 12 January 1869"],
    "card-04a": ["Albert J. Parkhouse, Timberlake Wire and Novelty Co.,",
                 "Jackson, Michigan \u2014 1903"],
    "card-06a": ["25 January 1904 \u2014 Charles L. Patterson files,",
                 "naming himself inventor"],
    "card-06b": ["U.S. Patent 822,981, granted 1906, assigned to",
                 "John B. Timberlake \u2014 then, an employee's invention",
                 "belonged to the employer"],
    "card-07a": ["Parkhouse left for Los Angeles \u2014 his own wire company"],
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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-28.json")))
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
        shifted = os.path.join(BASE, f"captions-test-28-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-28-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-28-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("27 - What If Coat Hangers Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("27 - What If Coat Hangers Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
