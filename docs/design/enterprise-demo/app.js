/**
 * UVAI /d enterprise design demo
 * Simulated playback — does NOT claim real WhisperX or WebRTC.
 */
(function () {
  'use strict';

  const DURATION_MS = 24000;
  const SCRUB_STEP_MS = 1000;

  /** Example word timings (ms) — demo data only */
  const WORDS = [
    { t: 0, w: 'Welcome' },
    { t: 520, w: 'to' },
    { t: 700, w: 'UVAI' },
    { t: 1100, w: 'Video' },
    { t: 1450, w: 'Pack.' },
    { t: 2100, w: 'Chapters' },
    { t: 2600, w: 'and' },
    { t: 2800, w: 'SOP' },
    { t: 3200, w: 'extract' },
    { t: 3700, w: 'from' },
    { t: 4000, w: 'this' },
    { t: 4300, w: 'READY' },
    { t: 4800, w: 'dogfood' },
    { t: 5300, w: 'clip.' },
    { t: 6200, w: 'Click' },
    { t: 6500, w: 'any' },
    { t: 6800, w: 'word' },
    { t: 7100, w: 'to' },
    { t: 7300, w: 'seek.' },
    { t: 8200, w: 'Bounding' },
    { t: 8700, w: 'boxes' },
    { t: 9100, w: 'are' },
    { t: 9350, w: 'EXAMPLE' },
    { t: 9900, w: 'DATA' },
    { t: 10400, w: 'behind' },
    { t: 10800, w: 'a' },
    { t: 11000, w: 'flag.' },
    { t: 11800, w: 'WebRTC' },
    { t: 12400, w: 'meter' },
    { t: 12800, w: 'is' },
    { t: 13000, w: 'SIMULATED' },
    { t: 13800, w: 'only—' },
    { t: 14400, w: 'no' },
    { t: 14600, w: 'live' },
    { t: 14900, w: 'RTC' },
    { t: 15300, w: 'claim.' },
    { t: 16200, w: 'Agent' },
    { t: 16600, w: 'cards' },
    { t: 17000, w: 'track' },
    { t: 17400, w: 'Extract,' },
    { t: 18100, w: 'Pack,' },
    { t: 18600, w: 'and' },
    { t: 18800, w: 'Verify.' },
    { t: 19800, w: 'MCP' },
    { t: 20200, w: 'log' },
    { t: 20500, w: 'uses' },
    { t: 20900, w: 'progressive' },
    { t: 21700, w: 'disclosure.' },
    { t: 22800, w: 'Claim' },
    { t: 23200, w: '≠' },
    { t: 23500, w: 'PASS.' }
  ];

  /** Timed bbox keyframes: { t0, t1, x, y, w, h, label } in % viewBox */
  const BBOXES = [
    { t0: 2000, t1: 7500, x: 18, y: 22, w: 42, h: 38, label: 'speaker' },
    { t0: 8000, t1: 14000, x: 48, y: 30, w: 36, h: 40, label: 'ui-panel' },
    { t0: 14500, t1: 21000, x: 12, y: 45, w: 55, h: 32, label: 'tool-surface' },
    { t0: 18000, t1: 24000, x: 62, y: 18, w: 28, h: 28, label: 'status-chip' }
  ];

  const AGENTS = [
    { id: 'extract', name: 'Extract', desc: 'Chapter + entity extraction', status: 'READY' },
    { id: 'pack', name: 'Pack', desc: 'SOP / pack assembly', status: 'PARTIAL' },
    { id: 'verify', name: 'Verify', desc: 'Grounding + QA checks', status: 'FAILED' }
  ];

  const MCP_LOG = [
    {
      tool: 'videopack.get',
      time: '14:02:11',
      payload: '{\n  "videoId": "XYMcBrFSJ4c",\n  "status": "READY"\n}'
    },
    {
      tool: 'transcript.words',
      time: '14:02:12',
      payload: '{\n  "count": 52,\n  "aligner": "demo-fixture"\n}'
    },
    {
      tool: 'agent.extract.run',
      time: '14:02:14',
      payload: '{\n  "chapters": 4,\n  "entities": 11\n}'
    },
    {
      tool: 'agent.pack.run',
      time: '14:02:18',
      payload: '{\n  "sopSections": 3,\n  "status": "PARTIAL"\n}'
    },
    {
      tool: 'agent.verify.run',
      time: '14:02:21',
      payload: '{\n  "status": "FAILED",\n  "reason": "citation_gap"\n}'
    },
    {
      tool: 'mcp.gateway.ping',
      time: '14:02:22',
      payload: '{\n  "ok": true,\n  "latencyMs": 42\n}'
    }
  ];

  const EVENTS = [
    { t: 0, m: 'Pack shell mounted (enterprise tokens).' },
    { t: 2100, m: 'Extract agent → READY.' },
    { t: 8200, m: 'EXAMPLE DATA bbox overlay active.' },
    { t: 11800, m: 'WebRTC control available (SIMULATED).' },
    { t: 16200, m: 'Pack agent → PARTIAL; Verify → FAILED.' },
    { t: 19800, m: 'MCP tool log disclosure expanded.' },
    { t: 22800, m: 'Reminder: Claim ≠ PASS.' }
  ];

  const state = {
    playing: false,
    t: 0,
    lastTs: 0,
    raf: 0,
    uiState: 'ready',
    bboxOn: true,
    webrtcOn: false,
    reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    vadRaf: 0
  };

  const $ = (id) => document.getElementById(id);

  function formatTime(ms) {
    const s = Math.max(0, ms) / 1000;
    const m = Math.floor(s / 60);
    const rem = s - m * 60;
    return `${String(m).padStart(2, '0')}:${rem.toFixed(1).padStart(4, '0')}`;
  }

  function chipClass(status) {
    if (status === 'READY') return 'chip chip-ready';
    if (status === 'PARTIAL') return 'chip chip-partial';
    return 'chip chip-failed';
  }

  /* ——— Render static panels ——— */
  function renderAgents() {
    const root = $('agent-cards');
    root.innerHTML = AGENTS.map(
      (a) => `
      <article class="agent-card" data-agent="${a.id}">
        <div class="agent-card-top">
          <span class="agent-name">${a.name}</span>
          <span class="${chipClass(a.status)}" aria-label="${a.name} status ${a.status}">${a.status}</span>
        </div>
        <div class="agent-desc">${a.desc}</div>
      </article>`
    ).join('');
  }

  function renderMcp() {
    const root = $('mcp-log');
    root.innerHTML = MCP_LOG.map(
      (row, i) => `
      <div class="mcp-row" role="listitem" data-i="${i}">
        <button type="button" class="mcp-row-summary" aria-expanded="false" aria-controls="mcp-payload-${i}" id="mcp-sum-${i}">
          <span class="mcp-chevron" aria-hidden="true">▸</span>
          <span class="mcp-tool">${row.tool}</span>
          <span class="mcp-time">${row.time}</span>
        </button>
        <pre class="mcp-payload" id="mcp-payload-${i}" hidden>${row.payload}</pre>
      </div>`
    ).join('');

    root.querySelectorAll('.mcp-row-summary').forEach((btn) => {
      btn.addEventListener('click', () => {
        const row = btn.closest('.mcp-row');
        const pre = row.querySelector('.mcp-payload');
        const open = pre.hasAttribute('hidden');
        if (open) {
          pre.removeAttribute('hidden');
          row.setAttribute('open', '');
          btn.setAttribute('aria-expanded', 'true');
        } else {
          pre.setAttribute('hidden', '');
          row.removeAttribute('open');
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    });
  }

  function renderTranscript() {
    const root = $('transcript');
    root.innerHTML = WORDS.map(
      (w, i) =>
        `<button type="button" class="word-btn" role="listitem" data-i="${i}" data-t="${w.t}" aria-label="Seek to ${formatTime(w.t)}: ${w.w}">${w.w}</button>`
    ).join(' ');

    root.querySelectorAll('.word-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        seekTo(Number(btn.dataset.t));
      });
    });
  }

  function renderEvents(activeT) {
    const root = $('event-stream');
    root.innerHTML = EVENTS.filter((e) => e.t <= activeT)
      .map(
        (e) => `
      <div class="event-row">
        <span class="event-t">${formatTime(e.t)}</span>
        <span class="event-m">${e.m}</span>
      </div>`
      )
      .join('');
  }

  /* ——— Playback ——— */
  function setPlaying(on) {
    state.playing = on;
    const btn = $('play-btn');
    btn.textContent = on ? '⏸' : '▶';
    btn.setAttribute('aria-label', on ? 'Pause' : 'Play');
    if (on) {
      state.lastTs = performance.now();
      state.raf = requestAnimationFrame(tick);
    } else if (state.raf) {
      cancelAnimationFrame(state.raf);
      state.raf = 0;
    }
  }

  function seekTo(ms) {
    state.t = Math.max(0, Math.min(DURATION_MS, ms));
    $('scrubber').value = String(state.t);
    paint(state.t);
    if (state.playing) state.lastTs = performance.now();
  }

  function tick(now) {
    if (!state.playing) return;
    const dt = now - state.lastTs;
    state.lastTs = now;
    state.t += dt;
    if (state.t >= DURATION_MS) {
      state.t = DURATION_MS;
      setPlaying(false);
    }
    $('scrubber').value = String(state.t);
    paint(state.t);
    if (state.playing) state.raf = requestAnimationFrame(tick);
  }

  function paint(t) {
    $('time-readout').textContent = `${formatTime(t)} / ${formatTime(DURATION_MS)}`;
    updateWords(t);
    updateBboxes(t);
    renderEvents(t);
  }

  function updateWords(t) {
    let active = -1;
    for (let i = 0; i < WORDS.length; i++) {
      if (WORDS[i].t <= t) active = i;
      else break;
    }
    document.querySelectorAll('.word-btn').forEach((btn, i) => {
      btn.classList.toggle('active', i === active);
      btn.classList.toggle('spoken', i < active);
    });
    const activeBtn = document.querySelector('.word-btn.active');
    if (activeBtn && state.playing) {
      const list = $('transcript');
      const br = activeBtn.getBoundingClientRect();
      const lr = list.getBoundingClientRect();
      if (br.top < lr.top || br.bottom > lr.bottom) {
        activeBtn.scrollIntoView({ block: 'nearest', behavior: state.reducedMotion ? 'auto' : 'smooth' });
      }
    }
  }

  function updateBboxes(t) {
    const svg = $('bbox-layer');
    const badge = $('bbox-badge');
    if (!state.bboxOn || state.uiState !== 'ready') {
      svg.innerHTML = '';
      badge.style.display = 'none';
      return;
    }
    badge.style.display = 'block';
    const active = BBOXES.filter((b) => t >= b.t0 && t <= b.t1);
    const pulse = state.reducedMotion ? 1 : 0.85 + 0.15 * Math.sin(t / 200);
    svg.innerHTML = active
      .map((b) => {
        const pad = state.reducedMotion ? 0 : (1 - pulse) * 1.2;
        return `
        <rect x="${b.x - pad}" y="${b.y - pad}" width="${b.w + pad * 2}" height="${b.h + pad * 2}"
          fill="rgba(56,189,248,0.12)" stroke="#38bdf8" stroke-width="0.6"
          vector-effect="non-scaling-stroke" rx="0.8" />
        <text x="${b.x}" y="${b.y - 1.5}" fill="#38bdf8" font-size="3" font-family="IBM Plex Mono, monospace">${b.label}</text>`;
      })
      .join('');
  }

  /* ——— WebRTC simulated ——— */
  function setWebrtc(on) {
    state.webrtcOn = on;
    $('webrtc-toggle').setAttribute('aria-pressed', String(on));
    $('webrtc-session-btn').setAttribute('aria-pressed', String(on));
    $('webrtc-session-btn').textContent = on ? 'End SIMULATED session' : 'WebRTC session';
    $('webrtc-panel').classList.toggle('active', on);
    if (on) {
      startVad();
    } else {
      stopVad();
      $('vad-fill').style.width = '0%';
      $('latency-readout').textContent = 'latency — ms';
    }
  }

  function startVad() {
    stopVad();
    const loop = () => {
      if (!state.webrtcOn) return;
      const level = state.reducedMotion
        ? 40
        : 15 + Math.abs(Math.sin(performance.now() / 180)) * 70 + Math.random() * 10;
      $('vad-fill').style.width = `${Math.min(100, level)}%`;
      const latency = state.reducedMotion ? 120 : 80 + Math.floor(Math.random() * 90);
      $('latency-readout').textContent = `latency ${latency} ms · SIMULATED`;
      state.vadRaf = requestAnimationFrame(loop);
    };
    state.vadRaf = requestAnimationFrame(loop);
  }

  function stopVad() {
    if (state.vadRaf) {
      cancelAnimationFrame(state.vadRaf);
      state.vadRaf = 0;
    }
  }

  /* ——— UI state matrix ——— */
  function setUiState(mode) {
    state.uiState = mode;
    document.querySelectorAll('.seg button[data-state]').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.state === mode));
    });

    const cols = ['agent', 'video', 'transcript'];
    cols.forEach((c) => {
      ['empty', 'loading', 'error', 'ready'].forEach((s) => {
        const el = $(`${c}-${s}`);
        if (!el) return;
        el.classList.toggle('visible', s === mode);
      });
    });

    const pack = $('pack-status');
    if (mode === 'ready') {
      pack.textContent = 'READY';
      pack.className = 'chip chip-ready';
    } else if (mode === 'loading') {
      pack.textContent = 'PARTIAL';
      pack.className = 'chip chip-partial';
    } else if (mode === 'error') {
      pack.textContent = 'FAILED';
      pack.className = 'chip chip-failed';
    } else {
      pack.textContent = 'EMPTY';
      pack.className = 'chip chip-sim';
    }

    if (mode !== 'ready' && state.playing) setPlaying(false);
    updateBboxes(state.t);
  }

  /* ——— Keyboard ——— */
  function onKey(e) {
    const tag = (e.target && e.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (e.code === 'Space') {
      e.preventDefault();
      if (state.uiState === 'ready') setPlaying(!state.playing);
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      seekTo(state.t - SCRUB_STEP_MS);
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      seekTo(state.t + SCRUB_STEP_MS);
    }
  }

  /* ——— Wire ——— */
  function init() {
    renderAgents();
    renderMcp();
    renderTranscript();
    renderEvents(0);
    paint(0);
    setUiState('ready');

    $('play-btn').addEventListener('click', () => {
      if (state.uiState !== 'ready') return;
      setPlaying(!state.playing);
    });

    $('scrubber').addEventListener('input', (e) => {
      seekTo(Number(e.target.value));
    });

    document.querySelectorAll('.seg button[data-state]').forEach((btn) => {
      btn.addEventListener('click', () => setUiState(btn.dataset.state));
    });

    $('bbox-toggle').addEventListener('click', () => {
      state.bboxOn = !state.bboxOn;
      $('bbox-toggle').setAttribute('aria-pressed', String(state.bboxOn));
      updateBboxes(state.t);
    });

    const syncWebrtcUi = (on) => setWebrtc(on);
    $('webrtc-toggle').addEventListener('click', () => syncWebrtcUi(!state.webrtcOn));
    $('webrtc-session-btn').addEventListener('click', () => syncWebrtcUi(!state.webrtcOn));

    window.addEventListener('keydown', onKey);

    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (ev) => {
      state.reducedMotion = ev.matches;
    });

    if (window.uvaiDemo && window.uvaiDemo.isElectron) {
      $('dogfood-meta').textContent = `electron · XYMcBrFSJ4c · v${window.uvaiDemo.version}`;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
