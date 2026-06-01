// Follow Supabase Edge Function format
// https://supabase.com/docs/guides/functions/quickstart

// Import Supabase Edge Function runtime
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

/**
 * Model Context Protocol (MCP) compatible edge function
 * This function handles context data for communication between models and components
 * @description Provides standardized context sharing between AI models and application components
 * @version 1.0.0
 *
 * Security: every request MUST present a valid Supabase JWT in the
 * `Authorization: Bearer <token>` header; anonymous requests are rejected with
 * 401. This in-function check is defense-in-depth on top of the platform-level
 * `verify_jwt = true` setting pinned in supabase/config.toml — never deploy
 * this function with `--no-verify-jwt`.
 */

// Types for MCP context
interface MCPContext {
  context_id?: string;
  operation?: string;
  parameters?: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  status?: string;
  timestamp?: number;
  error?: string | null;
  model_id?: string | null;
  metadata?: Record<string, unknown>;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

function jsonError(message: string, status: number): Response {
  return new Response(
    JSON.stringify({ status: "error", error: message }),
    { status, headers: JSON_HEADERS },
  );
}

// Handle HTTP request
serve(async (req) => {
  // --- Authentication: require a valid Supabase JWT --------------------------
  const authHeader = req.headers.get("Authorization") ?? "";
  const token = authHeader.match(/^Bearer\s+(.+)$/i)?.[1]?.trim();

  if (!token) {
    return jsonError("Missing or malformed Authorization header", 401);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY");

  if (!supabaseUrl || !supabaseAnonKey) {
    return jsonError("Authentication is not configured on the server", 500);
  }

  // Validate the bearer token against Supabase Auth (verifies signature + expiry).
  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${token}` } },
  });

  const { data: { user }, error: authError } = await supabase.auth.getUser(token);

  if (authError || !user) {
    return jsonError("Invalid or expired token", 401);
  }

  // --- Authenticated request handling ---------------------------------------
  const response: MCPContext = {
    context_id: crypto.randomUUID(),
    operation: "connect",
    status: "success",
    timestamp: Date.now(),
    model_id: null,
    result: {
      message: "MCP connection successful",
    },
  };

  // If this is a POST request, process the body
  if (req.method === "POST") {
    try {
      const body = await req.json();

      // Only reflect well-typed, expected fields back to the caller.
      if (typeof body?.modelId === "string") {
        response.model_id = body.modelId;
        response.result = { message: `Connected to model: ${body.modelId}` };
      }

      if (body?.context && typeof body.context === "object") {
        // Merge known string fields if provided
        if (typeof body.context.context_id === "string") {
          response.context_id = body.context.context_id;
        }
        if (typeof body.context.operation === "string") {
          response.operation = body.context.operation;
        }
      }
    } catch (_e) {
      response.status = "error";
      response.result = { message: "Error processing request" };
    }
  }

  // Return JSON response
  return new Response(JSON.stringify(response), { headers: JSON_HEADERS });
});
