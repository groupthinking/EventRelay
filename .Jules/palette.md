## 2024-07-13 - [Search Input Accessibility]
**Learning:** Found that search inputs and their corresponding submit buttons in the Dashboard panels were missing `aria-label` attributes, which can make it difficult for screen reader users to understand their purpose, especially since the input only had a placeholder.
**Action:** Always ensure that search inputs and icon/short-text submit buttons have explicit `aria-label` attributes to provide clear context to assistive technologies.
