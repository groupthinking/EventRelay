import { createHash } from "node:crypto";

export type Evidence = { id: string; seconds: number; endSeconds: number; text: string; kind: "audio" | "visual" };
export type Guide = { title: string; steps: { instruction: string; evidenceIds: string[]; inference: boolean }[]; gaps: string[] };

export function sourceIdentity(raw: string): { videoId: string; url: string } {
  const u = new URL(raw);
  if (u.protocol !== "https:" || u.username || u.password || u.port) throw new Error("unsupported_source");
  const host = u.hostname.toLowerCase();
  const id = host === "youtu.be" ? u.pathname.slice(1) : ["youtube.com", "www.youtube.com"].includes(host) && u.pathname === "/watch" ? u.searchParams.get("v") : null;
  if (!id || !/^[A-Za-z0-9_-]{11}$/.test(id)) throw new Error("unsupported_source");
  return { videoId: id, url: `https://www.youtube.com/watch?v=${id}` };
}

export function packEvidence(pack: any, videoId: string): { evidence: Evidence[]; sourceHash: string; gaps: string[] } {
  if (pack?.video_id !== videoId || sourceIdentity(pack.source_url).videoId !== videoId || !/^[a-f0-9]{64}$/i.test(pack?.provenance?.source_hash ?? "")) throw new Error("invalid_pack_identity");
  const evidence: Evidence[] = [];
  let chars = 0;
  for (const [i, s] of (pack.transcript?.segments ?? []).entries()) {
    if (!Number.isFinite(s.start_s) || !Number.isFinite(s.end_s) || s.start_s < 0 || s.end_s < s.start_s || typeof s.text !== "string" || !s.text.trim()) continue;
    const text = s.text.slice(0, 1200);
    if (chars + text.length > 12000 || evidence.length >= 100) break;
    evidence.push({ id: `audio-${i}`, seconds: s.start_s, endSeconds: s.end_s, text, kind: "audio" }); chars += text.length;
  }
  const audioCount = evidence.length;
  // A frame reference alone is not proof that its contents were analyzed.
  for (const [i, s] of (pack.visual_context?.visual_elements ?? []).entries()) {
    if (!Number.isFinite(s.timestamp) || s.timestamp < 0 || typeof s.content !== "string" || !s.content.trim() || !s.frame_path) continue;
    if (evidence.length - audioCount >= 24) break;
    evidence.push({ id: `visual-${i}`, seconds: s.timestamp, endSeconds: s.timestamp, text: s.content.slice(0, 600), kind: "visual" });
  }
  if (!audioCount) throw new Error("timestamped_audio_missing");
  const gaps = ["Visual observations cover sampled frames, not every moment."];
  if (evidence.length === audioCount) gaps.push("Visual analysis unavailable; this guide uses audio evidence only.");
  if ((pack.transcript?.segments?.length ?? 0) > audioCount) gaps.push("Transcript evidence was truncated to the request limit.");
  return { evidence, sourceHash: pack.provenance.source_hash, gaps };
}

export function validateGuide(value: any, evidence: Evidence[]): Guide {
  if (typeof value?.title !== "string" || !value.title.trim() || value.title.length > 200 || !Array.isArray(value.steps) || !value.steps.length || value.steps.length > 20 || !Array.isArray(value.gaps) || value.gaps.length > 20) throw new Error("invalid_guide");
  const ids = new Set(evidence.map(e => e.id));
  for (const s of value.steps) {
    if (typeof s.instruction !== "string" || !s.instruction.trim() || s.instruction.length > 1200 || typeof s.inference !== "boolean" || !Array.isArray(s.evidenceIds) || !s.evidenceIds.length || s.evidenceIds.length > 8 || s.evidenceIds.some((id: unknown) => typeof id !== "string" || !ids.has(id))) throw new Error("invalid_guide_citation");
  }
  if (value.gaps.some((s: unknown) => typeof s !== "string" || s.length > 800)) throw new Error("invalid_guide");
  return value;
}

function escape(text: string): string { return text.replace(/[\\`*_{}\[\]<>#!|]/g, c => `\\${c}`).replace(/[\r\n]+/g, " "); }
export function guideMarkdown(guide: Guide, evidence: Evidence[], source: string, gaps: string[]): string {
  const { url } = sourceIdentity(source);
  const byId = new Map(evidence.map(e => [e.id, e]));
  validateGuide(guide, evidence);
  return `# ${escape(guide.title)}\n\nSource: ${url}\n\n` + guide.steps.map((s, i) => `${i + 1}. ${s.inference ? "**Proposed decision:** " : ""}${escape(s.instruction)}\n   ${s.evidenceIds.map(id => { const e = byId.get(id)!; return `[${e.kind} ${e.seconds.toFixed(1)}s](${url}&t=${Math.floor(e.seconds)}s)`; }).join(" · ")}`).join("\n\n") + `\n\n## Coverage and unknowns\n${[...gaps, ...guide.gaps].map(s => `- ${escape(s)}`).join("\n")}\n\n## Source evidence\n${evidence.map(e => `- ${e.id} (${e.kind}, ${e.seconds.toFixed(1)}–${e.endSeconds.toFixed(1)}s): ${escape(e.text)}`).join("\n")}\n`;
}

export function guideId(userId: string, sourceHash: string, request: string): string {
  const h = createHash("sha256").update(JSON.stringify(["uvai-guide-v1", userId, sourceHash, request])).digest("hex");
  return `${h.slice(0,8)}-${h.slice(8,12)}-4${h.slice(13,16)}-a${h.slice(17,20)}-${h.slice(20,32)}`;
}
