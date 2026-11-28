import { test } from "node:test";
import assert from "node:assert/strict";
import { sourceIdentity, packEvidence, validateGuide, guideMarkdown, guideId } from "../lib/uvai/video-guide.ts";

// Deterministic fixtures only. These tests do not prove live extraction or model quality.
const source = "https://www.youtube.com/watch?v=auJzb1D-fag";
const pack = () => ({ video_id: "auJzb1D-fag", source_url: source, provenance: { source_hash: "a".repeat(64) }, transcript: { segments: [{ start_s: 2.5, end_s: 5, text: "Open settings" }] }, visual_context: null });
test("source validation rejects arbitrary hosts, credentials, ports and malformed ids", () => {
  for (const bad of ["https://localhost/watch?v=auJzb1D-fag", "https://youtube.com.evil.example/watch?v=auJzb1D-fag", "https://x:y@youtube.com/watch?v=auJzb1D-fag", "https://youtube.com:8443/watch?v=auJzb1D-fag", "http://youtu.be/auJzb1D-fag", "https://youtu.be/short"]) assert.throws(() => sourceIdentity(bad));
  assert.equal(sourceIdentity("https://youtu.be/auJzb1D-fag").url, source);
});
test("pack source mismatch cannot be used for guide grounding", () => {
  const p = pack(); p.source_url = "https://youtu.be/aaaaaaaaaaa";
  assert.throws(() => packEvidence(p, p.video_id), /invalid_pack_identity/);
});
test("untimed audio fails rather than inventing citations", () => {
  const p = pack(); p.transcript = { full_text: "Open settings", segments: [] };
  assert.throws(() => packEvidence(p, p.video_id), /timestamped_audio_missing/);
});
test("frame references alone never establish visual processing", () => {
  const p = pack(); p.keyframes = [{ t_s: 2, image_path: "/frame.jpg", desc: "Settings" }];
  const parsed = packEvidence(p, p.video_id);
  assert.equal(parsed.evidence.length, 1); assert.ok(parsed.gaps.some(s => s.includes("audio evidence only")));
});
test("visual observations retain provenance and sparse coverage disclaimer", () => {
  const p = pack(); p.visual_context = { visual_elements: [{ timestamp: 3, content: "Settings button", frame_path: "/frame.jpg" }] };
  const parsed = packEvidence(p, p.video_id); assert.equal(parsed.evidence[1].kind, "visual"); assert.ok(parsed.gaps.some(s => s.includes("not every moment")));
});
test("invented and absent citations fail closed", () => {
  const e = packEvidence(pack(), "auJzb1D-fag").evidence;
  for (const ids of [[], ["audio-999"], ["visual-0"]]) assert.throws(() => validateGuide({ title: "Guide", steps: [{ instruction: "Settings", evidenceIds: ids, inference: false }], gaps: [] }, e), /invalid_guide_citation/);
});
test("downloads contain timestamp links and escape source/model Markdown injection", () => {
  const e = packEvidence(pack(), "auJzb1D-fag").evidence;
  const g = { title: "Guide", steps: [{ instruction: "[click](javascript:alert(1))", evidenceIds: ["audio-0"], inference: true }], gaps: [] };
  const md = guideMarkdown(g, e, source, []);
  assert.ok(md.includes(`${source}&t=2s`)); assert.ok(md.includes("Proposed decision")); assert.ok(md.includes("\\[click\\]"));
});
test("reuse identity is isolated by user, source and requested outcome", () => {
  const a = guideId("alice", "a".repeat(64), "guide");
  assert.equal(a, guideId("alice", "a".repeat(64), "guide"));
  assert.notEqual(a, guideId("bob", "a".repeat(64), "guide"));
  assert.notEqual(a, guideId("alice", "b".repeat(64), "guide"));
  assert.notEqual(a, guideId("alice", "a".repeat(64), "spec"));
});

import { sourcePlayback } from "../lib/uvai/source-player.ts";
test("source player timestamps use only validated fixed-origin URLs", () => {
  const view = sourcePlayback("auJzb1D-fag", 62.9);
  assert.equal(view.label, "1:02");
  assert.equal(view.embed, "https://www.youtube-nocookie.com/embed/auJzb1D-fag?start=62");
  assert.equal(view.external, "https://www.youtube.com/watch?v=auJzb1D-fag&t=62s");
  for (const time of [-1, Infinity, NaN, 86401]) assert.throws(() => sourcePlayback("auJzb1D-fag", time));
  assert.throws(() => sourcePlayback("javascript:alert(1)", 0));
});
