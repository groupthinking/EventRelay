const howToJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'HowTo',
  name: 'Open the UVAI Studio workbench from a YouTube URL',
  description:
    'Paste a YouTube URL to open Studio and start a hashed Video Pack run. Transcript quality varies by source.',
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
      name: 'Open Studio',
      text: 'Studio starts a hashed Video Pack run (player, events, exports). Transcript quality varies by source.',
    },
    {
      '@type': 'HowToStep',
      position: 3,
      name: 'Use the workbench',
      text: 'Review Studio outputs when the run produces them. Not a guaranteed production E2E.',
    },
  ],
};

export function StructuredData() {
  return (
    <script type="application/ld+json">{JSON.stringify(howToJsonLd)}</script>
  );
}