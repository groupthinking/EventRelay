"use client";

import { useState } from "react";
import type { Evidence } from "@/lib/uvai/video-guide";
import { sourcePlayback } from "@/lib/uvai/source-player";

export function SourceEvidencePanel({ videoId, evidence }: { videoId: string; evidence: Evidence[] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const current = evidence.find(item => item.id === selected);
  let playback;
  try { playback = sourcePlayback(videoId, current?.seconds ?? 0); } catch { return <p role="alert">Source playback unavailable: invalid source timestamp.</p>; }
  return (
    <section aria-label="Video source evidence" className="mt-4 space-y-3">
      <p className="font-medium">Source evidence</p>
      <p className="text-muted-foreground">Transcript and sampled visual observations are source evidence. Proposed implementation decisions remain inference.</p>
      {current ? <iframe className="aspect-video w-full rounded border" title={`Video source at ${playback.label}`} src={playback.embed} sandbox="allow-scripts allow-same-origin allow-presentation" allow="fullscreen" referrerPolicy="strict-origin-when-cross-origin" loading="lazy" /> : <p className="text-muted-foreground">Select a timestamp to load the source player. Embedded playback depends on the source's access restrictions.</p>}
      <a href={playback.external} target="_blank" rel="noopener noreferrer" className="underline">Open source at {playback.label}</a>
      <ul className="max-h-64 space-y-2 overflow-y-auto" aria-label="Timestamped evidence">
        {evidence.map(item => {
          let timestamp;
          try { timestamp = sourcePlayback(videoId, item.seconds).label; } catch { return null; }
          return <li className="rounded border p-2" key={item.id}>
            <button type="button" className="font-medium underline" aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}>{timestamp} · {item.kind === "audio" ? "Transcript" : "Sampled visual observation"}</button>
            <p className="mt-1 whitespace-pre-wrap break-words">{item.text}</p>
          </li>;
        })}
      </ul>
    </section>
  );
}
