import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

// Exercise the schemas actually used by v0's transitive credential config.
// This loads schema code only; it never reads a user's credentials or calls Vercel.
const fromWeb = createRequire(join(process.cwd(), 'package.json'));
const fromV0 = createRequire(fromWeb.resolve('v0'));
const fromOidc = createRequire(fromV0.resolve('@vercel/oidc'));
const configEntry = fromOidc.resolve('@vercel/cli-config');
const schemas = fromOidc(join(dirname(configEntry), 'schema.zod.js'));

describe('v0 CLI configuration with patched Zod', () => {
  it('preserves valid global settings and strips unknown fields', () => {
    const settings = {
      credStorage: 'file',
      currentTeam: 'test-team',
      telemetry: { enabled: false },
      guidance: { enabled: true },
      updates: { auto: true, bypassMinReleaseAge: false },
      useNativeBinary: false,
    };
    expect(schemas.globalConfigSchema.parse({ ...settings, unexpected: true })).toEqual(settings);
  });

  it('rejects invalid credential storage and boolean settings', () => {
    expect(schemas.globalConfigSchema.safeParse({ credStorage: 'remote' }).success).toBe(false);
    expect(schemas.globalConfigSchema.safeParse({ telemetry: { enabled: 'yes' } }).success).toBe(false);
  });

  it('validates synthetic auth input and excludes source metadata from saved auth', () => {
    const auth = { token: 'synthetic-test-token', userId: 'test-user', expiresAt: 1234 };
    expect(schemas.authConfigSchema.parse({ ...auth, tokenSource: 'env' })).toEqual({
      ...auth,
      tokenSource: 'env',
    });
    expect(schemas.authFileConfigSchema.parse({ ...auth, tokenSource: 'env' })).toEqual(auth);
    expect(schemas.authConfigSchema.safeParse({ expiresAt: '1234' }).success).toBe(false);
    expect(schemas.authConfigSchema.safeParse({ tokenSource: 'remote' }).success).toBe(false);
  });
});
