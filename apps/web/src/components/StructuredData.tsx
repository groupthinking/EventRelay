const howToJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'HowTo',
  name: 'Turn a YouTube video into a workflow with UVAI',
  description:
    'Paste a YouTube URL, let UVAI extract transcript and events, then export or deploy actionable outputs.',
  step: [
    {
      '@type': 'HowToStep',
      position: 1,
      name: 'Paste URL',
      text: 'Submit a public YouTube link on uvai.io.',
    },
    {
      '@type': 'HowToStep',
      position: 2,
      name: 'Watch agents work',
      text: 'UVAI transcribes, extracts events, and streams pipeline progress.',
    },
    {
      '@type': 'HowToStep',
      position: 3,
      name: 'Get results',
      text: 'Download artifacts, handoff briefs, or deploy when adapters are configured.',
    },
  ],
};

export function StructuredData() {
  return (
    <script type="application/ld+json">{JSON.stringify(howToJsonLd)}</script>
  );
}