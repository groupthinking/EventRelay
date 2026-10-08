# UVAI Design Language — Locked 2026-10-02 (Hayden)

Source of truth for how UVAI looks. Written because Hayden said: "We need to
document our work or the agent will hallucinate." Do not invent a different
direction. When in doubt, match this document, not a trend.

## Product thesis (UNCHANGED)

UVAI extracts events from video, takes action, and provides deliverables.
Real results. Real action execution. This document changes only how the
artifacts of a build are packaged and presented — not what UVAI does.

## Design language: professional card system

Applies to ALL product surfaces: Studio workbench, output panes, hosted/built
app pages, export artifacts. ("All the above" — Hayden, 2026-10-02.)

- **Light, calm surfaces.** White cards on soft neutral backgrounds
  (soft blue-gray, not stark white page). Airy spacing.
- **Card = one structured idea.** Product image + structured data side by side.
  Sections inside cards: certifications, key documents, physical data,
  performance metrics — each with a small icon, a label, and a value.
  No dense IDE chrome in the output. No walls of undifferentiated text.
- **Typography:** clean grotesque, strong hierarchy. Brand small, title large,
  section labels small-caps-ish. Numbers and values plainly readable.
- **Documents are first-class.** PDF/document rows with file-type icon, title,
  and subtitle. Filterable (file type, document type) where lists grow.
- **Search is simple.** One search input, a few filter chips
  (e.g. category, data-type flags), then product cards with image + vendor +
  title. Three-up grid on desktop.
- **Floating contextual cards** for reference material (codes, standards):
  small pill cards that surface the current item plus amended/related items.
- **Professional, not playful.** This should feel like a tool a professional
  trusts with real work — closer to a building-products database than a
  hacker terminal.

## IDE model (from reference)

The interaction model is simple — "based on a simple concept" (Hayden):

1. Paste a YouTube URL. (One input. No ceremony.)
2. Generate. (The system does the work; show honest progress.)
3. Inspect the result in three views: **Render | Code | Spec.**
   - Render: the thing itself, previewed (phone frame for mobile, page for web).
   - Code: the real files, explorable, copyable.
   - Spec: the human-readable plan the build followed.
4. Chat alongside to iterate ("make changes, add new features, ask for anything").
5. Export: download the whole thing (zip) when it's right.

Dark mode is acceptable as a *viewer option* (the reference has a Dark mode
toggle), but the default product language is the light card system above.

## What NOT to do

- Do not bring back lime/ice-cream green. Ever.
- Do not build many differently-named panels that are all summaries.
  One card system, reused.
- Do not gate value behind sign-in. Sign-in restores a user's work only.
- Do not invent prices. Locked: Workflow Pro $39/mo or $390/yr,
  Maintain $199/mo per live product, Ship quoted per job.
- Do not compete on transcription. The differentiator is action/ship.

## References (Hayden's screenshots, 2026-10-02)

- Construction product cards: USG Durock (certifications, key documents,
  physical data, performance metrics), Viewrail Base Rail (product documents
  with filters), decking search (search + filter chips + product grid),
  building code reference (floating cards, diagrams/assemblies).
- Google AI Studio "Video to Learning App": paste-URL → generate,
  Render/Code/Spec tabs, phone preview, export zip, chat/preview toggle.
