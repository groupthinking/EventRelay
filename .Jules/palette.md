## 2025-10-24 - Accessibility improvements on Dashboard Panels
**Learning:** React `EmptyState` components (often simple icon + text) need ARIA `role="status"` and `aria-live="polite"` to be properly announced by screen readers when data loads or search results turn up empty. Custom buttons without an explicit `focus-visible` class might be skipped entirely by users navigating via keyboard.
**Action:** Always verify keyboard focus states and screen reader announcements for empty states and search result items.
