import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

// Static-source coverage for the video-generator disabled-state accessibility
// contract (see components/dashboard-search-accessibility.test.ts for the same
// pattern). The web suite runs in the `node` environment with no jsdom, so the
// button's rendered state is asserted from the source expressions that derive
// it rather than by mounting the component.
describe('video generator disabled-state accessibility', () => {
  const source = readSource('components/video-generator.tsx');

  const generateButton = source.match(/<button[\s\S]*?<\/button>/)?.[0];

  it('keeps the generate button disabled while the prompt is empty', () => {
    expect(generateButton).toBeDefined();
    // Empty/whitespace-only prompt (`!prompt.trim()`) disables the control, as
    // does an in-flight generation. Both conditions must remain in the guard.
    expect(generateButton).toContain("disabled={state === 'generating' || !prompt.trim()}");
  });

  it('associates the visible explanation only while the prompt is empty', () => {
    // aria-describedby points at the requirement text when the prompt is empty
    // and is dropped (undefined) once a non-whitespace prompt enables the
    // button, so assistive tech is not left describing an enabled control.
    expect(generateButton).toContain(
      "aria-describedby={!prompt.trim() ? 'video-generate-requirement' : undefined}",
    );
  });

  it('renders the requirement text with the referenced id only in the empty state', () => {
    // The described-by target is conditional on `!prompt.trim()`, so the id
    // that aria-describedby references exists exactly when the button is
    // disabled for an empty prompt and is removed once a prompt is entered.
    const requirement = source.match(
      /\{!prompt\.trim\(\) && \([\s\S]*?id="video-generate-requirement"[\s\S]*?<\/p>\s*\)\}/,
    )?.[0];

    expect(requirement).toBeDefined();
    expect(requirement).toContain('Enter a prompt to enable video generation.');
  });
});
