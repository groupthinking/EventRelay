## 2024-07-10 - [Accessibility] Improve video generator states and focus visibility
**Learning:** In long-running generation processes like video creation, simply disabling buttons isn't enough for screen readers. Using `aria-busy` and explicit `role="alert"` regions makes state changes much clearer. Also, character count limits for inputs should be linked directly via `aria-describedby` to provide immediate context.
**Action:** Pair `aria-busy` with disabled states on generation buttons, and ensure error messages are always contained within alert roles for immediate announcements.
