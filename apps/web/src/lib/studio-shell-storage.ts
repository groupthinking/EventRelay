/** localStorage keys for Studio three-panel shell layout (mirrors hosted /d prefix shape). */
export function studioShellStoragePrefix(videoId: string, sourceHash: string): string {
  return `uvai:studio-shell:${videoId}:${sourceHash}`;
}

export function loadStudioShellNumber(
  prefix: string,
  key: string,
  fallback: number,
): number {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = localStorage.getItem(`${prefix}:${key}`);
    if (!raw) return fallback;
    const n = Number(raw);
    return Number.isFinite(n) ? n : fallback;
  } catch {
    return fallback;
  }
}

export function saveStudioShellNumber(prefix: string, key: string, value: number): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(`${prefix}:${key}`, String(Math.round(value)));
  } catch {
    // quota / private mode
  }
}

export function loadStudioShellFlag(prefix: string, key: string): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(`${prefix}:${key}`) === '1';
  } catch {
    return false;
  }
}

export function saveStudioShellFlag(prefix: string, key: string, on: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(`${prefix}:${key}`, on ? '1' : '0');
  } catch {
    // ignore
  }
}
