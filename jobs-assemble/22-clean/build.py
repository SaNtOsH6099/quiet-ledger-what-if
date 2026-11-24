#!/usr/bin/env python3
"""Build Short 22 — "What If Towels Never Existed?"
Adapted from build_17.py (short-16-two-suns) + build_13.py (on-screen
text cards via drawtext, burned on BOTH cuts).

- Narration: narration-dominic-22b-norm.wav (41.23s, 48kHz).
  Ride is ALREADY in the mix (mix-22b.py): "weight," +3.0 dB,
  38.20-38.46 trim time. Norm is STATIC gain + limiter, NOT loudnorm
  dynamic: aresample=48000,volume=+0.40dB, alimiter=limit=0.80:level=0
  -> measured -16.10 LUFS, TP -1.90 dBTP on the rendered file. Ride
  re-verified on the rendered norm file (13/17 lesson): "weight,"
  0.316->0.468 peak; "27" untouched by the ride (0.677->0.709, static
  gain only); overall peak 0.80 = limiter cap.
- Items (video-time starts, 16 items, frames rendered on the GitHub
  farm): 01 0.00, 02 1.66, 03 3.92, 04 5.64, 05a 8.60, 05b 10.50,
  06 13.30, 07 15.24, 08a 18.96, 08b 20.56, 09 23.06, 10 26.22,
  11 29.88, 12 33.86, 13 35.74, 14 38.82. Video end 41.23.
  TPAD IS NEEDED (16 v1 lesson): the capture gives each item
  span*30+10 frames, but the xfade needs item i to last until the NEXT
  item's start + 0.25s, and the sentence-boundary silences leave gaps.
  item_pad() computes the hold per item from cfg-manifest-22.json.
  The hold is the natural visual — the scene holds while the
  narration pauses.
- Captions: captions-22.ass (23 events, max 2 lines, 80px, shadow-
  only, words present white + gold \\kf from RMS voiced ends —
  the kf-defect fix; digits rule: "400"/"27" merged tokens; the
  dropped "Then" has NO caption entry; "strigil" spelled correctly).
- On-screen text cards (drawtext, BOTH cuts, 13's pattern):
  05b "strigil — a curved bronze scraper" (10.50-12.60),
  07 "peshtemal" (15.24-18.12),
  10 "1851 — Queen Victoria ordered six dozen" (26.22-29.18),
  13 "cotton holds 27x its own weight" (35.74-38.46).
  Cards sit at y=1600, below the 40-60% caption band, so they never
  collide with the mid-frame captions.

Modes:
  python3 build_22.py test [--item N] [--at S]
      -> renders a 2.5s test clip of item N with captions, extracts
         a frame at clip time S.
  python3 build_22.py full
      -> full captioned render (41.23s)
  python3 build_22.py clean
      -> same render WITHOUT karaoke captions (cards still burned)
"""
import subprocess, sys, os, argparse, re

BASE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
XFADE = 0.25
NARR_END = 41.23
NARR_NORM = "narration-dominic-22b-norm.wav"
ASS = "captions-22.ass"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start, frames_dir, start_number, manifest_key) — frames are p_000.png (0-indexed)
ITEMS = [
    (0.00,  "frames-22-01", 0, "22-01"),
    (1.66,  "frames-22-02", 0, "22-02"),
    (3.92,  "frames-22-03", 0, "22-03"),
    (5.64,  "frames-22-04", 0, "22-04"),
    (8.60,  "frames-22-05a", 0, "22-05a"),
    (10.50, "frames-22-05b", 0, "22-05b"),
    (13.30, "frames-22-06", 0, "22-06"),
    (15.24, "frames-22-07", 0, "22-07"),
    (18.96, "frames-22-08a", 0, "22-08a"),
    (20.56, "frames-22-08b", 0, "22-08b"),
    (23.06, "frames-22-09", 0, "22-09"),
    (26.22, "frames-22-10", 0, "22-10"),
    (29.88, "frames-22-11", 0, "22-11"),
    (33.86, "frames-22-12", 0, "22-12"),
    (35.74, "frames-22-13", 0, "22-13"),
    (38.82, "frames-22-14", 0, "22-14"),
]

# (start, end, card_id) — card text files written by write_cards()
CARDS = [
    (10.50, 12.60, "card-05b"),
    (15.24, 18.12, "card-07"),
    (26.22, 29.18, "card-10"),
    (35.74, 38.46, "card-13"),
]
CARD_TEXT = {
    "card-05b": "strigil \u2014 a curved bronze scraper",
    "card-07": "peshtemal",
    "card-10": "1851 \u2014 Queen Victoria ordered six dozen",
    "card-13": "cotton holds 27x its own weight",
}


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


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


def item_pad(i):
    """Hold-last-frame pad (seconds) so item i lasts until the next item's
    start + XFADE (the transition needs BOTH inputs through its end).
    The capture gives each item span*30+10 frames, but the
    sentence-boundary silences leave gaps — without the pad the xfade
    chain truncates at the first short item (16 v1 build: video ended
    at 7.73s, where item 03's frames ran out). The gap is a narration
    silence, so holding the last frame is the natural visual."""
    import json
    man = json.load(open(os.path.join(BASE, "cfg-manifest-22.json")))
    st, d, sn, key = ITEMS[i]
    nframes = man[key]["frames"]
    have = nframes / FPS
    end = ITEMS[i + 1][0] + XFADE if i + 1 < len(ITEMS) else NARR_END
    need = end - st
    return max(0.0, need - have)


def build_filtergraph(ass_path=None):
    card_dir = write_cards()
    filters = []
    for i, (st, d, sn, key) in enumerate(ITEMS):
        pad = item_pad(i)
        tpad = f",tpad=stop_duration={pad:.3f}:stop_mode=clone" if pad > 0 else ""
        # stop_mode=clone is REQUIRED: tpad's default stop_mode=add appends
        # BLACK frames for the pad — 22's v1 shipped 7 black holes from this
        # (8.17s, 12.97s, 14.8s, 18.47s, 29.53s, 33.57s, 35.43s), found by
        # the hub's blackdetect scan 2026-11-24. Clone holds the last frame.
        filters.append(f"[{i}:v]format=yuv420p,settb=AVTB{tpad}[v{i}]")
    prev = "v0"
    for i in range(1, len(ITEMS)):
        off = ITEMS[i][0]
        out = f"x{i}" if i < len(ITEMS) - 1 else "vpre"
        filters.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={off}[{out}]")
        prev = out
    # on-screen text cards (both cuts)
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
        shifted = os.path.join(BASE, f"captions-test-22-shifted-item{args.item}.ass")
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
        out = os.path.join(BASE, f"test-clip-22-item{args.item}.mp4")
        run(["ffmpeg", "-y", "-framerate", "30", "-start_number", str(sn),
             "-i", os.path.join(BASE, d, "p_%03d.png"),
             "-filter_complex", ";".join(vf), "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-t", "2.5", "-crf", "19", out])
        frame = os.path.join(BASE, f"test-frame-22-item{args.item}.png")
        run(["ffmpeg", "-y", "-ss", str(args.at), "-i", out,
             "-frames:v", "1", frame])
        print(f"test frame: {frame} (absolute {shift + args.at:.2f}s)")
        return

    if args.mode == "full":
        render("22 - What If Towels Never Existed?.mp4",
               os.path.join(BASE, ASS))
        return

    if args.mode == "clean":
        render("22 - What If Towels Never Existed? (clean).mp4",
               None)
        return


if __name__ == "__main__":
    main()
