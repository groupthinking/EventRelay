# MCP-Compatible Supabase Edge Function: connect-to-cursor-mcp

This edge function implements the Model Context Protocol (MCP) for connecting to Cursor and other model-based systems. It provides a standardized way for models and components to exchange context information.

## What is MCP (Model Context Protocol)?

MCP is like a USB-C for AI - it provides a standard protocol for sharing context between models, tools, and applications. It enables structured, seamless context-sharing for smart, dynamic workflows in AI systems.

## Authentication

This function requires a valid Supabase JWT. Every request must include an
`Authorization: Bearer <token>` header (a user access token from Supabase Auth);
anonymous requests are rejected with `401`. JWT verification is enforced both by
the platform (`verify_jwt = true` in `supabase/config.toml`) and re-validated in
the function code. Do not deploy with `--no-verify-jwt`.

## Usage

The function expects a POST request with a JSON body containing:

```json
{
  "modelId": "string",  // ID of the model to connect to
  "context": {          // Optional MCP context object
    "context_id": "uuid-string",  // Optional, generated if not provided
    "operation": "string",        // connect, query, update, etc.
    "parameters": {},             // Operation-specific parameters
    "metadata": {}                // Additional metadata
  }
}
```

## Response Format

The function returns a structured MCP context response:

```json
{
  "context_id": "uuid-string",
  "model_id": "string",
  "operation": "string",
  "parameters": {},
  "result": {},
  "status": "success|error|pending",
  "error": null,
  "timestamp": 1714760000000,
  "metadata": {}
}
```

## Supported Operations

1. **connect** - Establishes a connection to a model
2. **query** - Queries for information with the given parameters
3. **update** - Updates the context with new information

## Example Curl Request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SUPABASE_USER_JWT" \
  -d '{"modelId": "gpt-4", "context": {"operation": "connect", "parameters": {"foo": "bar"}}}' \
  https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp
```

## Deployment

Deploy this function to your Supabase project:

```bash
supabase functions deploy connect-to-cursor-mcp
``` 