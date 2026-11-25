# Pack Ask pivot (option 1) — #2197 addendum

**Decision:** default `/d` hosted pack shell is light, calm, and chat-first
("Ask about this pack"). The dark enterprise console is opt-in telemetry,
not the default product surface.

## Reference patterns (user-supplied)

- Harvey playbook builder — serif headline, calm cards, guided start choices.
- UpCodes — floating `Pack (Current)`-style contextual card + supplement/update pills.
- Udacity AI Learning Assistant — verb tabs **Summarize / Extract / Escalate** beside active work.
- YouTube mobile `Ask about this video` — suggested-prompt chips + composer bottom sheet.

## What changed in the hosted shell

- `apps/web/src/styles/uvai-enterprise-tokens.css` — light `--uvai-*` defaults;
  dark values retained under `:root[data-pack-theme="enterprise-dark"]`.
- Emitted `src/styles.css` — `color-scheme: light` default, theme-aware chrome /
  nav / chat / bubbles, serif pack title (`--uvai-font-display`), prompt-chip
  styles, `max-width: 900px` bottom-sheet assistant on narrow viewports.
- Chat rail renamed to **Ask about this pack** with three suggested-prompt chips
  (Summarize the video / Recommend related content / List the key components).
  Chips and CTAs only fill the composer — they never fabricate answers.
- CTA verbs aligned to **Summarize / Extract / Escalate**. Escalate honestly
  sends as a normal pack chat message; the UI states there is no separate
  support queue on the page yet.
- Theme override: `?theme=enterprise-dark` (persisted to localStorage) restores
  the dark telemetry skin for ops/dev viewing.

## Claim ≠ PASS (unchanged)

No WhisperX, no real WebRTC/VAD, no <300ms turn-taking claim. Suggested prompts
are input helpers; every answer still comes from same-origin `/api/chat` over
stored pack fields only.
