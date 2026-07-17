## 2026-07-11 - Search Panel Accessibility Fixes
**Learning:** Adding visual feedback to `button` elements inside iterative search results, even when styled minimally, makes the UI drastically more intuitive for keyboard navigation and screen readers (by combining `focus-visible`, visual hover feedback, and `aria-busy` for loading states).
**Action:** When creating elements intended for user interaction, always pair visual interactivity (`hover`, `active`, and `disabled` opacities) with explicit semantic accessibility traits like `aria-busy` or robust `focus-visible` ring colors.
