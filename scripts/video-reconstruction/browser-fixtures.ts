import { readFileSync } from 'node:fs';
import { jsonText } from './local-files.ts';

export const fixtureImage = {
  name: 'illustrative-targets.jpg',
  mimeType: 'image/jpeg',
  buffer: readFileSync(new URL('./fixtures/illustrative-targets.jpg', import.meta.url)),
};
export const fixturePrompt = 'Organize the main ideas and supporting details by timestamp.';
export const fixtureSummary = {
  title: 'Illustrative test summary',
  sections: [
    {
      heading: 'Introduction',
      startSeconds: 0,
      endSeconds: 18,
      text: 'This synthetic example demonstrates the layout of an imported summary.',
    },
    {
      heading: 'Example workflow',
      startSeconds: 18,
      endSeconds: 64,
      text: 'Each section keeps its supplied time range and supporting notes together.',
    },
  ],
};
export const fixtureBoxes = {
  boxes: [
    { label: 'Illustration: display', x: 0.08, y: 0.13, width: 0.47, height: 0.69 },
    { label: 'Illustration: ring', x: 0.66, y: 0.34, width: 0.24, height: 0.40 },
  ],
};
export const exactFixtureBoxes = Buffer.from(jsonText(fixtureBoxes).replaceAll('\n', '\r\n'), 'utf8');
