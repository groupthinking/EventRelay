# UVAI Enterprise Design Demo

Interactive prototype for the UVAI Video Pack `/d` enterprise shell: design tokens, transcript sync, EXAMPLE DATA bboxes, SIMULATED WebRTC meter, agent/MCP telemetry.

**Does not claim** real WhisperX, real WebRTC, or live perception. See GitHub issue [#2197](https://github.com/groupthinking/EventRelay/issues/2197) and [`../UVAI_ENTERPRISE_DESIGN_AUDIT.md`](../UVAI_ENTERPRISE_DESIGN_AUDIT.md).

## Run

### Browser (no install)

Open `index.html` in Chrome/Edge/Firefox.

```bash
# optional local static server
npx --yes serve -p 5173 .
```

### Electron

```bash
npm install
npm start
```

## Demo controls

Header toggles: **Empty / Loading / Error / Ready** state matrix, bbox flag, WebRTC SIMULATED session.

Keyboard: **Space** play/pause, **←/→** scrub ~1s (when focus is not in a text field).

Dogfood reference: https://uvai.io/d/XYMcBrFSJ4c
