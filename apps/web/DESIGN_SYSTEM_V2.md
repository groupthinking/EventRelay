# UVAI Design System — Muse-based Rebuild (2026-10-07)

CEO decision: full site rebuild on Muse's design language. The old site read as AI slop. This is the new foundation.

## Design principles (from Muse)

1. **Warm minimalism.** Warm off-white surfaces, not stark white, not cold blue-gray. The page feels like paper, not glass.
2. **Typography leads.** Clear hierarchy, generous line height, comfortable measure. Type does the work; decoration doesn't.
3. **Calm surfaces.** Subtle 1px borders over shadows. Cards sit quietly on the page.
4. **One accent, restrained.** A single warm accent color for actions and focus. Everything else is neutral.
5. **Breathing room.** Generous spacing everywhere. Nothing cramped, nothing shouting.
6. **No decoration.** Every element earns its place. No gradients, no glow, no glassmorphism, no emoji-as-UI.

## Tokens

### Color
- `--uvai-bg`: #FAF9F7 (warm paper — page background)
- `--uvai-surface`: #FFFFFF (cards, elevated surfaces)
- `--uvai-border`: #E8E5E0 (warm hairline borders)
- `--uvai-ink`: #1C1B1A (primary text, warm near-black)
- `--uvai-ink-soft`: #6B675F (secondary text, warm gray)
- `--uvai-ink-faint`: #A8A29A (tertiary text, placeholders)
- `--uvai-accent`: #C2410C (warm burnt orange — primary actions, focus)
- `--uvai-accent-soft`: #FFF3EB (accent tint for highlights)
- `--uvai-success`: #2F7D4F (quiet green, confirmations only)
- `--uvai-warn`: #B45309 (quiet amber, warnings only)
- `--uvai-danger`: #B3261E (quiet red, destructive only)

### Typography
- **Display/headlines:** Newsreader or Source Serif 4, light to regular. Warm, editorial, trustworthy.
- **Body/UI:** Inter, regular/medium. Clean, readable, neutral.
- **Mono (code/labels only):** IBM Plex Mono or system mono. Never for body text.
- Scale: 12 / 14 / 16 / 20 / 24 / 32 / 40 / 48. Tight leading on display (1.1), relaxed on body (1.6).

### Spacing
- Base unit 4px. Generous section padding (64–96px desktop). Card padding 24–32px. Nothing below 16px between related elements.

### Radius & border
- Cards: 12px radius, 1px solid var(--uvai-border). No shadow by default; subtle shadow (0 1px 2px rgba(0,0,0,0.04)) on hover/interactive only.
- Buttons: 8px radius. Primary = accent fill, white text. Secondary = transparent with border.
- Inputs: 8px radius, 1px border, warm focus ring (accent at 20% opacity).

## Component rules

- **Buttons:** Two variants only (primary accent, secondary outline). No gradient buttons. No pill buttons except small chips.
- **Cards:** White, hairline border, 12px radius. One idea per card. Icon + label + value rows inside.
- **Nav:** Minimal top bar. Wordmark left, 2–3 links, one CTA. No mega-menus.
- **Empty states:** Honest, quiet. One line of text, one action. No illustrations, no emoji.
- **Loading:** Subtle skeleton or quiet spinner. No playful animations.
- **No:** gradients, glassmorphism, glow effects, emoji in UI chrome, lime green, dark hacker-terminal aesthetic, walls of undifferentiated text.

## What stays locked (from before)

- Product thesis: action extractor, not summarizer.
- Paywall at export: Workflow Pro $39/mo or $390/yr.
- Sign-in restores work only; never gates value.
- G.A.T.E. stays exactly PASS | HOLD | REJECT | ESCALATE.
- No invented prices. No competing on transcription.
