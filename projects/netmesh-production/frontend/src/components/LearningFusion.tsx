import React, { useEffect, useMemo, useRef, useState } from 'react';

// Lightweight icons (inline SVG) to avoid extra deps
const Icon = {
  Split: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M3 4h8v16H3V4zm10 0h8v16h-8V4z" />
    </svg>
  ),
  External: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3z" />
      <path d="M5 5h5V3H3v7h2V5zm14 14h-5v2h7v-7h-2v5zM5 19v-5H3v7h7v-2H5z" />
    </svg>
  ),
  Info: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M11 7h2v2h-2V7zm0 4h2v6h-2v-6zm1-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
    </svg>
  ),
  Plus: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M11 11V5h2v6h6v2h-6v6h-2v-6H5v-2h6z" />
    </svg>
  ),
  Trash: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M6 7h12v14H6z" opacity=".3"/><path d="M15.5 4l-1-1h-5l-1 1H5v2h14V4zM7 21c0 1.1.9 2 2 2h6c1.1 0 2-.9 2-2V7H7v14z"/>
    </svg>
  ),
  Min: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M6 13h12v-2H6v2z" />
    </svg>
  ),
  Max: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M7 14h10v2H7zM7 8h10v2H7z" />
    </svg>
  ),
  Pen: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1.003 1.003 0 0 0 0-1.42l-2.34-2.34a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.84-1.82z" />
    </svg>
  ),
  Eraser: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M16.24 3.56L7.11 12.68l3.54 3.54 9.13-9.12-3.54-3.54zM3 18.36V21h7.76l-3.54-3.54H3z" />
    </svg>
  ),
  Download: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M5 20h14v-2H5v2zM11 4h2v8h3l-4 4-4-4h3V4z" />
    </svg>
  ),
};

// Types
export type ResourceItem = {
  id: string;
  title: string;
  url: string;
  source: 'LinkedIn' | 'Apple Developer' | 'Apple' | 'External';
  description?: string;
  progress?: number;
};

// Utils
function rnd(): string {
  try {
    // @ts-ignore
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch {}
  return Math.random().toString(36).slice(2);
}

function loadLocal<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : fallback;
  } catch {
    return fallback;
  }
}

function saveLocal<T>(key: string, val: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch {}
}

// Compute blocked state without touching cross-origin objects
export function computeBlockedState(loadFired: boolean, elapsedMs: number, timeoutMs: number): boolean {
  return !loadFired && elapsedMs >= timeoutMs;
}

// Styles
const styles = {
  page: { minHeight: '100vh', background: '#0a0a0a', color: '#e5e5e5', fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif' },
  header: { position: 'sticky' as const, top: 0, zIndex: 40, backdropFilter: 'blur(6px)', borderBottom: '1px solid #262626', background: 'rgba(10,10,10,0.6)' },
  headerInner: { maxWidth: 1120, margin: '0 auto', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 },
  title: { fontSize: 18, fontWeight: 600 },
  btn: { padding: '8px 12px', borderRadius: 12, border: '1px solid #3f3f46', background: 'transparent', color: '#e5e5e5', cursor: 'pointer' },
  main: { maxWidth: 1120, margin: '0 auto', padding: '24px 16px', display: 'grid', gap: 24, gridTemplateColumns: '1fr' },
  card: { border: '1px solid #262626', background: 'rgba(18,18,18,0.6)', borderRadius: 16, padding: 16 },
  badge: { padding: '4px 8px', borderRadius: 8, border: '1px solid #3f3f46', fontSize: 12 },
  input: { width: '100%', padding: '10px 12px', borderRadius: 14, border: '1px solid #262626', background: '#0a0a0a', color: '#e5e5e5', outline: 'none' as const },
  footer: { maxWidth: 1120, margin: '0 auto', padding: '8px 16px 24px', color: '#a3a3a3', fontSize: 12 },
};

// Card
function Card({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section style={styles.card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: '#d4d4d4' }}>
        {icon}
        <h2 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: 16, borderRadius: 12, border: '1px dashed #262626', color: '#a3a3a3', fontSize: 14, textAlign: 'center' }}>{children}</div>
  );
}

function SourceBadge({ source }: { source: ResourceItem['source'] }) {
  const map: Record<string, React.CSSProperties> = {
    LinkedIn: { background: 'rgba(2,132,199,0.2)', color: '#7dd3fc', borderColor: 'rgba(2,132,199,0.6)' },
    Apple: { background: '#1a1a1a', color: '#e5e5e5', borderColor: '#3f3f46' },
    'Apple Developer': { background: '#1a1a1a', color: '#e5e5e5', borderColor: '#3f3f46' },
    External: { background: 'rgba(16,185,129,0.2)', color: '#86efac', borderColor: 'rgba(16,185,129,0.6)' },
  };
  const style = { ...styles.badge, ...(map[source] || map['External']) };
  return <span style={style}>{source}</span>;
}

function UrlAdder({ onAdd }: { onAdd: (url: string) => void }) {
  const [url, setUrl] = useState('');
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <input style={styles.input} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Paste LinkedIn Learning / Apple WWDC / vidIQ link" />
      <button style={styles.btn} onClick={() => { if (url) { onAdd(url); setUrl(''); } }}>
        <Icon.Plus /> Add
      </button>
    </div>
  );
}

// Cross-origin-safe iframe wrapper
function SafeFrame({ url }: { url?: string }) {
  const [blocked, setBlocked] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [startAt, setStartAt] = useState<number>(Date.now());
  const TIMEOUT_MS = 3000;

  useEffect(() => { setBlocked(false); setLoaded(false); setStartAt(Date.now()); }, [url]);
  useEffect(() => {
    const t = setInterval(() => {
      const elapsed = Date.now() - startAt;
      if (computeBlockedState(loaded, elapsed, TIMEOUT_MS)) { setBlocked(true); clearInterval(t); }
      if (loaded) clearInterval(t);
    }, 200);
    return () => clearInterval(t);
  }, [loaded, startAt]);

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ aspectRatio: '16/9', width: '100%', overflow: 'hidden', borderRadius: 12, border: '1px solid #262626', background: '#000' }}>
        <iframe
          src={url}
          onLoad={() => { setLoaded(true); setBlocked(false); }}
          style={{ width: '100%', height: '100%', border: 0 }}
          allow="autoplay; encrypted-media; picture-in-picture"
          title="embedded"
        />
      </div>
      {blocked && (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(10,10,10,0.8)', backdropFilter: 'blur(3px)', borderRadius: 12, border: '1px solid #262626', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, textAlign: 'center', padding: 16 }}>
          <div style={{ fontSize: 14, color: '#d4d4d4' }}>This provider likely blocks in‑page embeds. Open it in a new tab.</div>
          {url && (
            <a href={url} target="_blank" rel="noreferrer" style={{ ...styles.btn, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Icon.External /> Open Resource
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function Panel({ title, url }: { title: string; url: string }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ fontSize: 13, color: '#d4d4d4' }}>{title}</div>
        <a href={url} target="_blank" rel="noreferrer" style={{ ...styles.btn, fontSize: 12, padding: '6px 8px', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Icon.External /> Open
        </a>
      </div>
      <SafeFrame url={url} />
    </div>
  );
}

function AppleSessionHelper() {
  const [session, setSession] = useState<'243' | '259'>('243');
  const base = `https://developer.apple.com/videos/play/wwdc2025/${session}/`;
  const openTab = () => window.open(base, '_blank');

  return (
    <Card title="WWDC Session Guide" icon={<Icon.Info />}> 
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr', alignItems: 'start' }}>
        <div>
          <div style={{ fontSize: 14, color: '#d4d4d4', marginBottom: 8 }}>Session</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(['243','259'] as const).map((id) => (
              <button key={id} onClick={() => setSession(id)} style={{ ...styles.btn, borderColor: session===id? '#0284c7':'#3f3f46', background: session===id? 'rgba(2,132,199,0.1)':'transparent' }}>#{id}</button>
            ))}
            <button onClick={openTab} style={{ ...styles.btn, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Icon.External /> Open Full Page
            </button>
          </div>
          <div style={{ marginTop: 8, color: '#a3a3a3', fontSize: 12 }}>Mirrors the page layout: <b>About</b> • <b>Summary</b> • <b>Transcript</b> • <b>Code</b>.</div>
        </div>
        <div>
          <SafeFrame url={base} />
        </div>
      </div>
    </Card>
  );
}

function CanvasLab() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [last, setLast] = useState<[number, number]>([0, 0]);
  const [mode, setMode] = useState<'pen' | 'eraser'>('pen');

  useEffect(() => {
    const c = canvasRef.current; if (!c) return; const ctx = c.getContext('2d'); if (!ctx) return; ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0,0,c.width,c.height);
  }, []);

  function loadImage(file?: File) {
    const c = canvasRef.current; if (!c || !file) return; const ctx = c.getContext('2d'); if (!ctx) return; const img = new Image();
    img.onload = () => { const scale = Math.min(c.width/img.width, c.height/img.height); const w = img.width*scale, h = img.height*scale; const x=(c.width-w)/2, y=(c.height-h)/2; ctx.drawImage(img, x,y,w,h); };
    img.src = URL.createObjectURL(file);
  }

  function onPointerDown(e: React.PointerEvent<HTMLCanvasElement>) { const c = canvasRef.current; if (!c) return; const r = c.getBoundingClientRect(); setIsDrawing(true); setLast([e.clientX-r.left, e.clientY-r.top]); }
  function onPointerMove(e: React.PointerEvent<HTMLCanvasElement>) { const c = canvasRef.current; if (!c || !isDrawing) return; const r=c.getBoundingClientRect(); const ctx=c.getContext('2d'); if(!ctx) return; const [lx,ly]=last; const x=e.clientX-r.left, y=e.clientY-r.top; ctx.strokeStyle = mode==='pen'? '#ffffff':'#0a0a0a'; ctx.lineWidth = mode==='pen'? 2:14; ctx.lineCap='round'; ctx.beginPath(); ctx.moveTo(lx,ly); ctx.lineTo(x,y); ctx.stroke(); setLast([x,y]); }
  function onPointerUp() { setIsDrawing(false); }
  function clearCanvas() { const c = canvasRef.current; if (!c) return; const ctx=c.getContext('2d'); if(!ctx) return; ctx.fillStyle='#0a0a0a'; ctx.fillRect(0,0,c.width,c.height); }
  function download() { const c = canvasRef.current; if(!c) return; const url = c.toDataURL('image/png'); const a=document.createElement('a'); a.href=url; a.download='canvas-note.png'; a.click(); }

  return (
    <Card title="Canvas (Sketchnotes)" icon={<Icon.Info />}> 
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <button onClick={() => setMode('pen')} style={{ ...styles.btn, borderColor: mode==='pen'? '#0284c7':'#3f3f46', background: mode==='pen'? 'rgba(2,132,199,0.1)':'transparent' }}><Icon.Pen /> Pen</button>
        <button onClick={() => setMode('eraser')} style={{ ...styles.btn, borderColor: mode==='eraser'? '#0284c7':'#3f3f46', background: mode==='eraser'? 'rgba(2,132,199,0.1)':'transparent' }}><Icon.Eraser /> Eraser</button>
        <button onClick={clearCanvas} style={styles.btn}>Clear</button>
        <button onClick={download} style={styles.btn}><Icon.Download /> Export PNG</button>
        <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => loadImage(e.target.files?.[0])} />
        <button onClick={() => fileRef.current?.click()} style={styles.btn}>Import Screenshot</button>
        <div style={{ fontSize: 12, color: '#a3a3a3' }}>Tip: import WWDC screenshots and annotate About/Summary/Transcript/Code.</div>
      </div>
      <div style={{ borderRadius: 12, border: '1px solid #262626', overflow: 'hidden' }}>
        <canvas ref={canvasRef} width={1200} height={600} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} style={{ width: '100%', height: 380, background: '#0a0a0a' }} />
      </div>
    </Card>
  );
}

function TipCard() {
  return (
    <div style={{ borderRadius: 16, border: '1px solid #262626', background: 'rgba(18,18,18,0.3)', padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#d4d4d4', marginBottom: 8 }}>
        <Icon.Info /> <span style={{ fontSize: 14, fontWeight: 600 }}>Pro tips</span>
      </div>
      <ul style={{ paddingLeft: 20, fontSize: 14, color: '#a3a3a3', margin: 0 }}>
        <li>Use Split View to keep LinkedIn Learning and the WWDC session side‑by‑side.</li>
        <li>Session helper mirrors the WWDC layout; tabs open the official page.</li>
        <li>Use the Canvas to annotate screenshots and export a PNG for sharing.</li>
      </ul>
    </div>
  );
}

// Main component
export default function LearningFusion(): JSX.Element {
  const defaultItems = useMemo<ResourceItem[]>(() => [
    { id: rnd(), title: 'LinkedIn Learning', url: 'https://www.linkedin.com/learning/?trk=nav_neptune_learning&', source: 'LinkedIn', description: 'Browse professional courses across business, tech, and creative.' },
    { id: rnd(), title: 'WWDC25 – Session 243 (UIKit updates)', url: 'https://developer.apple.com/videos/play/wwdc2025/243/', source: 'Apple Developer', description: 'Official Apple WWDC 2025 session #243 video.' },
    { id: rnd(), title: 'WWDC25 – Session 259', url: 'https://developer.apple.com/videos/play/wwdc2025/259/', source: 'Apple Developer', description: 'Another relevant WWDC session for cross‑reference.' },
    { id: rnd(), title: 'vidIQ – Channel Dashboard', url: 'https://app.vidiq.com/channels/UCdIOP8Q-gNpqx8kK-PQDoDA/dashboard', source: 'External', description: 'Performance dashboard for the target YouTube channel.' },
  ], []);

  const [catalog, setCatalog] = useState<ResourceItem[]>(() => loadLocal<ResourceItem[]>('lf_catalog', defaultItems));
  const [playlist, setPlaylist] = useState<ResourceItem[]>(() => loadLocal<ResourceItem[]>('lf_playlist', []));
  const [notes, setNotes] = useState<string>(() => localStorage.getItem('lf_notes') || '');
  const [showSplit, setShowSplit] = useState<boolean>(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  const activeItem = useMemo<ResourceItem | undefined>(() =>
    catalog.find((c) => c.id === activeId) || catalog.find((c) => (c.source || '').includes('Apple')) || catalog[0]
  , [catalog, activeId]);

  useEffect(() => saveLocal('lf_catalog', catalog), [catalog]);
  useEffect(() => saveLocal('lf_playlist', playlist), [playlist]);
  useEffect(() => localStorage.setItem('lf_notes', notes), [notes]);

  function addToPlaylist(itemId: string) {
    const item = catalog.find((c) => c.id === itemId); if (!item) return;
    if (playlist.some((p) => p.id === itemId)) return;
    setPlaylist([...playlist, { ...item, progress: 0 }]);
  }
  function removeFromPlaylist(itemId: string) { setPlaylist(playlist.filter((p) => p.id !== itemId)); }
  function updateProgress(itemId: string, progress: number) { setPlaylist(playlist.map((p) => (p.id === itemId ? { ...p, progress } : p))); }

  function addCustom(url: string) {
    if (!url) return;
    const id = rnd();
    const title = url.includes('linkedin.com/learning') ? 'LinkedIn Learning (custom)' : url.includes('developer.apple.com/videos') ? 'Apple Developer Video (custom)' : 'Learning Link';
    const source: ResourceItem['source'] = url.includes('linkedin.com') ? 'LinkedIn' : url.includes('apple.com') ? 'Apple Developer' : 'External';
    const item: ResourceItem = { id, title, url, source, description: 'User‑added resource.' };
    setCatalog([item, ...catalog]); setActiveId(id);
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon.Split />
            <h1 style={styles.title}>Learning Fusion</h1>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={() => setShowSplit(!showSplit)} style={styles.btn}>{showSplit ? <Icon.Min /> : <Icon.Max />} {showSplit ? 'Single View' : 'Split View'}</button>
            {activeItem?.url && (
              <a href={activeItem.url} target="_blank" rel="noreferrer" style={styles.btn}><Icon.External /> Open Active</a>
            )}
          </div>
        </div>
      </header>

      {/* Responsive columns */}
      <style>{`@media(min-width:1024px){ .lf-grid { display:grid; grid-template-columns: 1fr 2fr; gap:24px; } }`}</style>

      <main className="lf-grid" style={styles.main as React.CSSProperties}>
        {/* Left: Catalog */}
        <section>
          <Card title="Catalog">
            <UrlAdder onAdd={addCustom} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {catalog.map((item) => (
                <div key={item.id} style={{ padding: 12, borderRadius: 14, border: `1px solid ${activeId === item.id ? '#0284c7' : '#262626'}`, background: activeId === item.id ? 'rgba(2,132,199,0.1)' : 'rgba(18,18,18,0.6)', display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer' }} onClick={() => setActiveId(item.id)}>
                  <div><SourceBadge source={item.source} /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.title}</div>
                    <div style={{ fontSize: 12, color: '#a3a3a3', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.url}</div>
                    {item.description && <div style={{ fontSize: 12, color: '#a3a3a3', marginTop: 4 }}>{item.description}</div>}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button onClick={(e) => { e.stopPropagation(); addToPlaylist(item.id); }} style={styles.btn}><Icon.Plus /> Queue</button>
                    <a href={item.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} style={{ ...styles.btn, padding: 8 }}><Icon.External /></a>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 12, color: '#a3a3a3', marginTop: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Icon.Info /> Some providers (LinkedIn Learning, Apple Developer) block iframes. Use Open if the preview fails.
            </div>
          </Card>

          <Card title="Playlist">
            {playlist.length === 0 && <EmptyState>Nothing queued yet. Add items from the Catalog.</EmptyState>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {playlist.map((p) => (
                <div key={p.id} style={{ padding: 12, borderRadius: 14, border: '1px solid #262626', background: 'rgba(18,18,18,0.6)' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <SourceBadge source={p.source} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.title}</div>
                      <div style={{ fontSize: 12, color: '#a3a3a3', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.url}</div>
                    </div>
                    <button onClick={() => removeFromPlaylist(p.id)} style={{ ...styles.btn, padding: 8 }} aria-label="Remove"><Icon.Trash /></button>
                  </div>
                  <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input type="range" min={0} max={100} step={5} value={p.progress || 0} onChange={(e) => updateProgress(p.id, Number(e.currentTarget.value))} style={{ flex: 1 }} />
                    <div style={{ fontSize: 12, width: 32, textAlign: 'right' }}>{p.progress ?? 0}%</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Notes">
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Capture insights, TODOs, timestamps…" style={{ width: '100%', height: 160, borderRadius: 14, border: '1px solid #262626', background: '#0a0a0a', color: '#e5e5e5', padding: 12, fontSize: 14, outline: 'none' }} />
            <div style={{ fontSize: 12, color: '#a3a3a3', marginTop: 8 }}>Auto‑saved locally.</div>
          </Card>
        </section>

        {/* Right: Viewer & helpers */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <Card title="Viewer">
            {!showSplit ? (
              <SafeFrame url={activeItem?.url} />
            ) : (
              <div style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr' }}>
                <Panel title="LinkedIn Learning" url="https://www.linkedin.com/learning/?trk=nav_neptune_learning&" />
                <Panel title="WWDC – Session 243" url="https://developer.apple.com/videos/play/wwdc2025/243/" />
              </div>
            )}
          </Card>

          <AppleSessionHelper />
          <CanvasLab />
          <TipCard />
        </section>
      </main>

      <footer style={styles.footer}>Built for combining LinkedIn Learning, Apple WWDC resources, and hands‑on sketching in one workflow.</footer>
    </div>
  );
}


