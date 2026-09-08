#!/usr/bin/env node

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import {
  auth,
  extractWWWAuthenticateParams,
  UnauthorizedError,
} from '@modelcontextprotocol/sdk/client/auth.js';
import { checkResourceAllowed } from '@modelcontextprotocol/sdk/shared/auth-utils.js';

const SCENARIOS = new Set([
  'auth/metadata-var2',
  'auth/token-endpoint-auth-basic',
  'auth/token-endpoint-auth-post',
  'auth/token-endpoint-auth-none',
]);

const CIMD_CLIENT_METADATA_URL =
  'https://conformance-test.local/client-metadata.json';

class ConformanceOAuthProvider {
  constructor(redirectUrl, clientMetadata, clientMetadataUrl) {
    this._redirectUrl = redirectUrl;
    this._clientMetadata = clientMetadata;
    this._clientMetadataUrl = clientMetadataUrl;
  }

  get redirectUrl() {
    return this._redirectUrl;
  }

  get clientMetadata() {
    return this._clientMetadata;
  }

  get clientMetadataUrl() {
    return this._clientMetadataUrl;
  }

  clientInformation() {
    return this._clientInformation;
  }

  saveClientInformation(clientInformation) {
    this._clientInformation = clientInformation;
  }

  tokens() {
    return this._tokens;
  }

  saveTokens(tokens) {
    this._tokens = tokens;
  }

  async redirectToAuthorization(authorizationUrl) {
    const response = await fetch(authorizationUrl.toString(), {
      redirect: 'manual',
    });
    const location = response.headers.get('location');
    if (!location) {
      throw new Error(`No redirect location received from ${authorizationUrl}`);
    }
    const redirectUrl = new URL(location);
    const code = redirectUrl.searchParams.get('code');
    if (!code) {
      throw new Error('No authorization code in redirect URL');
    }
    this._authCode = code;
  }

  async getAuthCode() {
    if (!this._authCode) {
      throw new Error('No authorization code available');
    }
    return this._authCode;
  }

  saveCodeVerifier(codeVerifier) {
    this._codeVerifier = codeVerifier;
  }

  codeVerifier() {
    if (!this._codeVerifier) {
      throw new Error('No code verifier saved');
    }
    return this._codeVerifier;
  }

  validateResourceURL(defaultResource, configuredResource) {
    if (!configuredResource) {
      return undefined;
    }
    if (
      !checkResourceAllowed({
        requestedResource: defaultResource,
        configuredResource,
      })
    ) {
      throw new Error(
        `Protected resource ${configuredResource} does not match expected ${defaultResource} (or origin)`
      );
    }
    return { href: configuredResource };
  }
}

function unionScopes(prior, challenged) {
  const values = [...(prior?.split(' ') ?? []), ...(challenged?.split(' ') ?? [])]
    .map((value) => value.trim())
    .filter(Boolean);
  return values.length ? [...new Set(values)].join(' ') : undefined;
}

async function handle401(response, provider, next, serverUrl) {
  const { resourceMetadataUrl, scope: challengedScope } =
    extractWWWAuthenticateParams(response);
  const prior = (await provider.tokens())?.scope;
  const scope = unionScopes(prior, challengedScope);

  let result = await auth(provider, {
    serverUrl,
    resourceMetadataUrl,
    scope,
    fetchFn: next,
  });

  if (result === 'REDIRECT') {
    const authorizationCode = await provider.getAuthCode();
    result = await auth(provider, {
      serverUrl,
      resourceMetadataUrl,
      scope,
      authorizationCode,
      fetchFn: next,
    });
  }

  if (result !== 'AUTHORIZED') {
    throw new UnauthorizedError(`Authentication failed with result: ${result}`);
  }
}

function withOAuthRetry(clientName, baseUrl, clientMetadataUrl) {
  const provider = new ConformanceOAuthProvider(
    'http://localhost:3000/callback',
    {
      client_name: clientName,
      redirect_uris: ['http://localhost:3000/callback'],
      application_type: 'native',
    },
    clientMetadataUrl
  );

  return (next) => {
    return async (input, init) => {
      const makeRequest = async () => {
        const headers = new Headers(init?.headers);
        const tokens = await provider.tokens();
        if (tokens?.access_token) {
          headers.set('Authorization', ['Bearer', tokens.access_token].join(' '));
        }
        return next(input, { ...init, headers });
      };

      let response = await makeRequest();
      if (response.status === 401 || response.status === 403) {
        await handle401(response, provider, next, baseUrl);
        response = await makeRequest();
      }
      if (response.status === 401 || response.status === 403) {
        const url = typeof input === 'string' ? input : input.toString();
        throw new UnauthorizedError(`Authentication failed for ${url}`);
      }
      return response;
    };
  };
}

async function runAuthClient(serverUrl) {
  const client = new Client(
    { name: 'eventrelay-conformance-client', version: '1.0.0' },
    { capabilities: {} }
  );
  const oauthFetch = withOAuthRetry(
    'eventrelay-conformance-client',
    new URL(serverUrl),
    CIMD_CLIENT_METADATA_URL
  )(fetch);
  const transport = new StreamableHTTPClientTransport(new URL(serverUrl), {
    fetch: oauthFetch,
  });
  await client.connect(transport);
  await client.listTools();
  await client.callTool({ name: 'test-tool', arguments: {} });
  await transport.close();
}

async function main() {
  const scenario = process.env.MCP_CONFORMANCE_SCENARIO;
  const serverUrl = process.argv[2];

  if (!scenario || !serverUrl) {
    throw new Error('Usage: MCP_CONFORMANCE_SCENARIO=<scenario> official_mcp_auth_client.mjs <server-url>');
  }
  if (!SCENARIOS.has(scenario)) {
    throw new Error(`Unsupported conformance scenario: ${scenario}`);
  }
  await runAuthClient(serverUrl);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
