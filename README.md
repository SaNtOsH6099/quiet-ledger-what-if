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
- Never commit a finished video, narration, or caption file here. This repo
  holds the renderer + per-job inputs (stills + cfg) + nothing else.
- Job folders are inputs, not archives: once an item's frames are downloaded
  and verified, the job folder may be removed to keep the repo light.
