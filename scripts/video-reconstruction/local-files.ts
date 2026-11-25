import {
  closeSync, constants, fstatSync, lstatSync, openSync, readFileSync, realpathSync, writeFileSync,
} from 'node:fs';
import { dirname, isAbsolute, resolve } from 'node:path';

export function requireDirectory(path: string): void {
  if (!isAbsolute(path) || resolve(path) !== path || !lstatSync(path).isDirectory() || realpathSync(path) !== path) {
    throw new Error(`Expected an absolute directory without symbolic links: ${path}`);
  }
}

export function readLocalFile(path: string, maxBytes: number): Buffer {
  requireDirectory(dirname(path));
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const stat = fstatSync(fd);
    if (!stat.isFile() || stat.nlink !== 1 || stat.size > maxBytes) throw new Error(`Unsafe or oversized file: ${path}`);
    const data = readFileSync(fd);
    if (data.length !== stat.size) throw new Error(`File changed while reading: ${path}`);
    return data;
  } finally {
    closeSync(fd);
  }
}

export function parseJsonBytes(bytes: Uint8Array): unknown {
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}

export function readJson(path: string, maxBytes = 1_048_576): unknown {
  return parseJsonBytes(readLocalFile(path, maxBytes));
}

export function writeNew(path: string, data: string | Uint8Array): void {
  requireDirectory(dirname(path));
  writeFileSync(path, data, { mode: 0o600, flag: 'wx' });
}

export function jsonText(value: unknown): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}
