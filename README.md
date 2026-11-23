# quiet-ledger-what-if — render farm

GitHub Actions render farm for the **Echoes of What If** Shorts. All heavy
rendering (particle captures) runs here, in parallel, one workflow run per
item. **Nothing renders locally.**

## How it works

- `render/scene.html` — the generic Three.js particle renderer (three
  0.187.0). Driven entirely by a cfg JSON passed as `?cfg=<base64>`: the
  still (`bg`), frame count, zoom, figure, foreground, particle systems,
  overlays, glows, rects. Same renderer the local pipeline used for Shorts
  13–16, with the import map pointed at the repo's own `node_modules`.
- `render/capture.js` — Node (no npm deps). Spawns headless Chrome with CDP,
  loads the scene, calls `window.renderFrame(n)` + `Page.captureScreenshot`
  for each frame, writes `p_%03d.png` frames. Ported from the proven local
  `capture-16.js`.
- `.github/workflows/render.yml` — `workflow_dispatch` per item. Installs
  three, serves the repo on port 8123, renders, verifies the frame count
  against the cfg, uploads the frames as an artifact (`frames-<job>`,
  30-day retention).

## Running a render (one item)

1. Push the job inputs to this repo:
   - `jobs/<job>/cfg.txt` — the cfg JSON, base64-encoded (same format as the
     local `cfg-<N>-<ITEM>.txt`). Its `bg` must be the server-root-relative
     still path: `/jobs/<job>/still.png`.
   - `jobs/<job>/still.png` — the 1080x1920 still the particles render over.
   - (`fg` and any other asset the cfg references must also be under
     `jobs/<job>/` with matching paths in the cfg.)
2. Dispatch the workflow with `job=<job>` (GitHub UI → Actions → render-item
   → Run workflow, or the API).
3. When the run finishes, download the `frames-<job>` artifact. It holds
   exactly `frames` PNGs (`p_000.png` …). Verify the count, then assemble
   locally with ffmpeg (assembly is a fast composite, not a render).

Run one workflow per item — items render in parallel on separate runners.
A full video is 12 items; each takes roughly the local time (~10–15 min)
but all 12 run at once instead of sequentially.

## Assembling a video (ffmpeg, on GitHub — never local)

Every type of render runs on GitHub Actions, including the final ffmpeg
assembly (full captioned cut + clean cut). No ffmpeg runs on the VM.

1. Push the assembly package to this repo under `jobs-assemble/<job>/`:
   - `build.py` — the video's assembly script (ffmpeg filtergraph: tpad +
     xfade chain + drawtext cards + subtitles for the full cut).
   - `narration-norm.wav` — the mixed, levelled narration (rides + static
     gain + limiter already applied; assembly only composites it).
   - `captions.ass` — karaoke captions, full cut only.
   - `cfg-manifest.json` — frame counts per item (drives the tpad hold).
   - `frames.txt` — one frame-artifact name per line
     (e.g. `frames-21-01a`), in the same order as the build script's items.
   The job id is `<video>-<cut>`, e.g. `21-full` / `21-clean`.
2. Dispatch `.github/workflows/assemble.yml` with `job=<job>`,
   `mode=full| clean`. The workflow downloads the frame artifacts from this
   repo, installs ffmpeg + DejaVu if missing, runs `build.py <mode>`,
   verifies the mp4 (ffprobe duration + moov), then uploads it as artifact
   `assemble-<job>` (30-day retention).
3. Download the artifact, rename `<job>.mp4` back to the deliverable name
   (`NN - What If ... Existed?.mp4` / `... (clean).mp4`), verify it
   (duration, resolution, loudness, frame spot-check vs the reference),
   then upload to Drive per the 3-file rule.
4. Delete the `jobs-assemble/<job>/` folder from the repo once the mp4 is
   downloaded and verified — assembly inputs are transient, like job
   folders.

Gotcha: GitHub Artifacts rejects NTFS-unsafe characters in filenames, and
our deliverable names contain `?` ("What If ... Existed?.mp4"). The
workflow renames the mp4 to the safe `<job>.mp4` before upload; the hub
renames it back after download. Never try to upload the `?` name directly.

## Local test (optional)

```sh
npm install
python3 -m http.server 8123 &
CFG_FILE=jobs/<job>/cfg.txt SCENE_URL=http://127.0.0.1:8123/render/scene.html \
  OUT_DIR=frames-<job> CHROME_BIN=$(which google-chrome || which chromium) \
  node render/capture.js
```

## Repo rules

- Zero cost: public repo, free unlimited Actions minutes. No secrets, no
  API keys, no credentials in this repo — ever.
- Never commit a finished video here. Narration, captions and build scripts
  ARE committed, but only as transient assembly inputs under
  `jobs-assemble/<job>/`, deleted once the mp4 is downloaded and verified.
- Job folders are inputs, not archives: once an item's frames are downloaded
  and verified, the job folder may be removed to keep the repo light.
