<<<<<<< HEAD:.Jules/palette.md
## 2025-10-24 - Accessibility improvements on Dashboard Panels
**Learning:** React `EmptyState` components (often simple icon + text) need ARIA `role="status"` and `aria-live="polite"` to be properly announced by screen readers when data loads or search results turn up empty. Custom buttons without an explicit `focus-visible` class might be skipped entirely by users navigating via keyboard.
**Action:** Always verify keyboard focus states and screen reader announcements for empty states and search result items.
=======
## 2026-07-13 - Search Input Accessibility
**Learning:** Search inputs still need an explicit programmatic label when the only visible prompt is a placeholder, but a submit button with visible text like `Go` should usually rely on that visible text for its accessible name so voice-control users can activate it by name.
**Action:** Add a real label (or equivalent programmatic name) to placeholder-only search inputs, and only add an `aria-label` to short-text submit buttons when it includes the visible button text.
## 2026-07-14 - Scrubber Keyboard Accessibility
**Learning:** Adding keyboard event listeners (like `onKeyDown`) to custom interactive elements (like a `div` acting as a scrubber/slider) doesn't automatically expose those shortcuts to screen readers.
**Action:** Always add `aria-keyshortcuts` to custom ARIA widgets (like `role="slider"`) to announce available keyboard commands (e.g., "ArrowLeft ArrowRight Home End") when the element receives focus.
>>>>>>> origin/main:.jules/palette.md
