/**
 * Uncompressed ZIP (store method). One download instead of N blobs,
 * so Chrome actually saves the official starter + DEPLOY.md.
 */

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[i] = c >>> 0;
  }
  return table;
})();

function crc32(bytes: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) {
    c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function u16(value: number): Uint8Array {
  const out = new Uint8Array(2);
  new DataView(out.buffer).setUint16(0, value, true);
  return out;
}

function u32(value: number): Uint8Array {
  const out = new Uint8Array(4);
  new DataView(out.buffer).setUint32(0, value, true);
  return out;
}

function concat(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

export function zipUtf8Files(files: Record<string, string>): Uint8Array {
  const encoder = new TextEncoder();
  const locals: Uint8Array[] = [];
  const centrals: Uint8Array[] = [];
  let offset = 0;

  for (const [rawPath, content] of Object.entries(files)) {
    const path = rawPath.replace(/\\/g, '/').replace(/^\/+/, '');
    if (!path) continue;
    const name = encoder.encode(path);
    const data = encoder.encode(content);
    const crc = crc32(data);
    const size = data.length;
    const local = concat([
      encoder.encode('PK\u0003\u0004'),
      u16(20),
      u16(1 << 11),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(size),
      u32(size),
      u16(name.length),
      u16(0),
      name,
      data,
    ]);
    locals.push(local);
    centrals.push(
      concat([
        encoder.encode('PK\u0001\u0002'),
        u16(20),
        u16(20),
        u16(1 << 11),
        u16(0),
        u16(0),
        u16(0),
        u32(crc),
        u32(size),
        u32(size),
        u16(name.length),
        u16(0),
        u16(0),
        u16(0),
        u16(0),
        u32(0),
        u32(offset),
        name,
      ]),
    );
    offset += local.length;
  }

  const central = concat(centrals);
  const end = concat([
    encoder.encode('PK\u0005\u0006'),
    u16(0),
    u16(0),
    u16(centrals.length),
    u16(centrals.length),
    u32(central.length),
    u32(offset),
    u16(0),
  ]);
  return concat([...locals, central, end]);
}

export function zipEntryNames(zip: Uint8Array): string[] {
  const names: string[] = [];
  const decoder = new TextDecoder();
  let i = 0;
  while (i + 30 < zip.length) {
    if (zip[i] !== 0x50 || zip[i + 1] !== 0x4b || zip[i + 2] !== 0x03 || zip[i + 3] !== 0x04) {
      break;
    }
    const nameLen = zip[i + 26] | (zip[i + 27] << 8);
    const extraLen = zip[i + 28] | (zip[i + 29] << 8);
    const size = zip[i + 22] | (zip[i + 23] << 8) | (zip[i + 24] << 16) | (zip[i + 25] << 24);
    names.push(decoder.decode(zip.subarray(i + 30, i + 30 + nameLen)));
    i += 30 + nameLen + extraLen + size;
  }
  return names;
}
