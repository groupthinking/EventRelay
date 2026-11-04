# Key page dependency trees

These trees identify the current UX structure and the source files Superdesign should use for faithful reproduction before branching.

## Landing `/`

```text
apps/web/src/app/page.tsx
├── landing/LandingNav.tsx
├── landing/HeroSection.tsx
├── landing/BentoFeatures.tsx
├── landing/WorkflowSection.tsx
├── landing/TemplatesSection.tsx
├── landing/DeveloperSection.tsx
├── landing/ContactSection.tsx
└── landing/LandingFooter.tsx
```

## Analysis library/workspace `/dashboard`

```text
apps/web/src/app/dashboard/page.tsx
├── Nav.tsx
├── billing/BillingStatusBanner.tsx
├── PreferencesPanel.tsx
├── dashboard/DashboardCanvasView.tsx
│   ├── dashboard/VideoCanvasStage.tsx
│   └── dashboard/panels.tsx
├── dashboard/DashboardSplitView.tsx
├── store/dashboard-store.ts
└── types/dashboard.ts
```

## Workflow studio `/studio`

```text
apps/web/src/app/studio/page.tsx
└── components/VideoWorkflowStudio.tsx
    ├── lib/studio-generation.ts
    ├── lib/studio-agent-tools.ts
    └── lib/studio-deploy.ts
```

## Features `/features`

```text
apps/web/src/app/features/page.tsx
├── Nav.tsx
└── Footer.tsx
```

## Pricing `/pricing`

```text
apps/web/src/app/pricing/page.tsx
├── Nav.tsx
├── billing/ProCheckoutButton.tsx
└── Footer.tsx
```

## Playground `/playground`

```text
apps/web/src/app/playground/page.tsx
├── Nav.tsx
└── pipeline/chat/video components and API routes
```

Page entry sources remain authoritative in `apps/web/src/app/**/page.tsx`; the files above are the dependency map Superdesign should use to select focused context without duplicating route source into this index.
