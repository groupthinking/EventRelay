## 2024-07-14 - Scrubber Keyboard Accessibility
**Learning:** Adding keyboard event listeners (like `onKeyDown`) to custom interactive elements (like a `div` acting as a scrubber/slider) doesn`t automatically expose those shortcuts to screen readers.
**Action:** Always add `aria-keyshortcuts` to custom ARIA widgets (like `role="slider"`) to announce available keyboard commands (e.g., "ArrowLeft ArrowRight Home End") when the element receives focus.
