// Verify the installed code at its consumers, independent of npm advisory names.
const assert = require('node:assert/strict');
const { existsSync } = require('node:fs');
const { createRequire } = require('node:module');
const { resolve } = require('node:path');
const test = require('node:test');
const lock = require('../../package-lock.json');

test('installed glob consumers resolve the reviewed matcher and retain file selection', () => {
  const root = resolve(__dirname, '../..');
  const consumers = new Set();
  for (const [location, pkg] of Object.entries(lock.packages)) {
    if (!['dependencies', 'optionalDependencies', 'peerDependencies']
      .some(field => Object.hasOwn(pkg[field] || {}, 'picomatch'))) continue;
    const manifest = resolve(root, location, 'package.json');
    if (!existsSync(manifest) && pkg.optional) continue;
    const local = createRequire(manifest);
    const match = local('picomatch');
    assert.equal(local('picomatch/package.json').name, '@ryotsu/picomatch', location);
    const clips = match('clips/**/*.{mp4,webm}', { ignore: '**/drafts/**' });
    assert.ok(clips('clips/take.mp4') && clips('clips/approved/take.webm'));
    assert.ok(!clips('clips/drafts/take.mp4') && !clips('clips/take.wav'));
    assert.equal(match.scan('clips/*.mp4').base, 'clips');
    const compiled = match.makeRe('+(take*.mp4)');
    assert.ok(compiled.test('take01.mp4'));
    assert.doesNotMatch(compiled.source, /\)[+*]/, 'redundant unbounded repetition');
    consumers.add(location.split('node_modules/').pop());
  }
  for (const required of ['micromatch', 'tinyglobby', 'vite', 'vitest']) {
    assert.ok(consumers.has(required), required + ' was not checked');
  }
});
