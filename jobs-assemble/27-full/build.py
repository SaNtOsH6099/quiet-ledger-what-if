#!/usr/bin/env python3
"""Build Short 27 — "What If Bobby Pins Never Existed?"
Adapted from build_21.py (short-20-chopsticks).

- Narration: narration-dominic-27a-norm.wav (47.87s, 48kHz).
  Rides are ALREADY in the mix (mix-27a.py): S3 tilt +1.0, S4 +1.5,
  S5 +2.0, S6 +2.5 dB; word rides "her" +5.0, "machines" +2.0,
  "grip" +2.0, "included" +4.5. Norm is STATIC gain + limiter,
  NOT loudnorm dynamic: aresample=48000,volume=+0.80dB,
  alimiter=limit=0.80:level=0 -> measured -16.09 LUFS, TP -1.87 dBTP
  on the norm file (mix measured -16.80 / -0.81). Rides re-verified
  on the norm file: every window +0.75 to +0.96 dB over the mix,
  155 samples at the 0.80 cap.
- Items (video-time starts, 17 items, frames rendered on the GitHub
  farm): 01a 0.00, 01b 2.40, 01c 4.80, 02a 8.04, 02b 10.50, 02c 12.30,
  03a 14.33, 03b 17.20, 03c 19.80, 04a 22.65, 04b 26.00, 05a 29.61,
  05b 33.00, 05c 35.60, 06a 38.76, 06b 42.00, 06c 45.00.
  Video end 47.87.
  On-screen text cards (6, from stills-plan.md, drawtext per build_13.py,
  y=1600 below the caption band, on BOTH cuts):
  02a "hairpins ~5500 BC, Hemudu, China",
  02c "Kirby, Beard & Co., Birmingham, by 1853 — in Britain still the kirby grip",
  03a "Irene Castle, 1914 — the Castle bob (reportedly 20,000 women a week, 1915)",
  04a "Luis Marcus, San Francisco, after WWI — two pins, 35 cents; named for the bob, the short 1920s haircut",
  05a "Veronica Lake, 1943 — U.S. government asked her to pin back her peek-a-boo hair",
  06a "one side flat, one side wavy — the waves grip".
  Card widths measured with PIL at 36px (DejaVuSans): 02c 1292px,
  03a 1410px, 04a 1874px, 05a 1492px — all too wide for one 1080px
  line, so those four are split into TWO lines (drawtext renders the
  newline; block stays centred, max line 959px).
  02a 639px and 06a 828px stay one line. Kirby card MUST land at the
  02c beat (load-bearing); do NOT stretch 03b.
  v1 DEFECT (found at Gate 5 frame QC, fixed in v2): a newline inside
  one drawtext textfile renders a TOFU BOX at the end of the first
  line (all four two-line cards) — the fix is one drawtext filter PER
  LINE (y=1600 + 45*line), never a newline inside a textfile.
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-27.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-27.ass (23 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "7,000"/"1914,"/"20,000"/"35 cents,"/
  "1943," merged tokens). Zero sync notes from the generator.

Modes:
  python3 build_27.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_27.py full
      -> full captioned render (47.87s)
  python3 build_27.py clean
      -> same render WITHOUT karaoke captions
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 47.87
NARR_NORM = "narration-dominic-27a-norm.wav"
ASS = "captions-27.ass"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-27-01a", 0, "27-01a"),
    (2.40,  "frames-27-01b", 0, "27-01b"),
    (4.80,  "frames-27-01c", 0, "27-01c"),
    (8.04,  "frames-27-02a", 0, "27-02a"),
    (10.50, "frames-27-02b", 0, "27-02b"),
    (12.30, "frames-27-02c", 0, "27-02c"),
    (14.33, "frames-27-03a", 0, "27-03a"),
    (17.20, "frames-27-03b", 0, "27-03b"),
    (19.80, "frames-27-03c", 0, "27-03c"),
    (22.65, "frames-27-04a", 0, "27-04a"),
    (26.00, "frames-27-04b", 0, "27-04b"),
    (29.61, "frames-27-05a", 0, "27-05a"),
    (33.00, "frames-27-05b", 0, "27-05b"),
    (35.60, "frames-27-05c", 0, "27-05c"),
    (38.76, "frames-27-06a", 0, "27-06a"),
    (42.00, "frames-27-06b", 0, "27-06b"),
    (45.00, "frames-27-06c", 0, "27-06c"),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, end, card_id) — card text files written by write_cards()
# Windows sit inside their scene's beat; Kirby card at the 02c beat.
CARDS = [
    (8.20, 10.40, "card-02a"),
    (12.45, 14.25, "card-02c"),
    (14.50, 17.10, "card-03a"),
    (22.85, 25.90, "card-04a"),
    (29.80, 32.90, "card-05a"),
    (38.95, 41.90, "card-06a"),
]
CARD_TEXT = {
    "card-02a": ["hairpins ~5500 BC, Hemudu, China"],
    "card-02c": ["Kirby, Beard & Co., Birmingham, by",
                 "1853 \u2014 in Britain still the kirby grip"],
    "card-03a": ["Irene Castle, 1914 \u2014 the Castle bob",
                 "(reportedly 20,000 women a week, 1915)"],
    "card-04a": ["Luis Marcus, San Francisco, after WWI \u2014 two pins,",
                 "35 cents; named for the bob, the short 1920s haircut"],
    "card-05a": ["Veronica Lake, 1943 \u2014 U.S. government",
                 "asked her to pin back her peek-a-boo hair"],
    "card-06a": ["one side flat, one side wavy \u2014 the waves grip"],
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
    man = json.load(open(os.path.join(BASE, "cfg-manifest-27.json")))
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
        shifted = os.path.join(BASE, f"captions-test-27-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-27-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-27-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("27 - What If Bobby Pins Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("27 - What If Bobby Pins Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
