import { describe, expect, it } from 'vitest';
import { canonicalYouTubeSource, resolveYouTubeSourceId } from '../video-source-identity';

const ID = 'auJzb1D-fag';
describe('YouTube source identity confinement', () => {
  it('canonicalizes each supported URL without preserving supplied authority or tracking', () => {
    for (const source of [ID, `https://youtu.be/${ID}?si=tracking`, `https://www.youtube.com/watch?v=${ID}&t=3`, `https://m.youtube.com/shorts/${ID}`, `https://youtube.com/embed/${ID}`]) {
      expect(resolveYouTubeSourceId(source)).toBe(ID);
      expect(canonicalYouTubeSource(ID, source)).toBe(`https://www.youtube.com/watch?v=${ID}`);
    }
  });
  it('rejects deceptive hosts, protocols, credentials, ports, path confusion and ambiguous identity', () => {
    for (const source of [
      `https://attacker.example/x/youtube.com/watch?v=${ID}`, `https://youtube.com.attacker.example/watch?v=${ID}`,
      `http://youtube.com/watch?v=${ID}`, `https://user@youtube.com/watch?v=${ID}`, `https://youtube.com:443/watch?v=${ID}`,
      `https://youtube.com\\@attacker.example/watch?v=${ID}`, `https://youtube.com/watch?v=${ID}&v=jNQXAC9IVRw`,
      `https://youtu.be/${ID}/extra`, `https://youtube.com/watch?v=${ID}extra`, `https://%79outube.com/watch?v=${ID}`,
      `https://youtube.com/redirect?q=https://youtu.be/${ID}`, `//youtube.com/watch?v=${ID}`, `https://you\ntube.com/watch?v=${ID}`,
    ]) expect(resolveYouTubeSourceId(source)).toBeNull();
  });
  it('rejects disagreement between valid IDs and never treats a supplied URL as authority', () => {
    expect(() => canonicalYouTubeSource(ID, 'https://youtu.be/jNQXAC9IVRw')).toThrow('does not match');
    expect(() => canonicalYouTubeSource('invalid')).toThrow('Invalid YouTube');
  });
});
