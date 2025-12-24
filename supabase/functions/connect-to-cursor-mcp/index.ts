// Follow Supabase Edge Function format
// https://supabase.com/docs/guides/functions/quickstart

// Import Supabase Edge Function runtime
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

/**
 * Model Context Protocol (MCP) compatible edge function
 * This function handles context data for communication between models and components
 * @description Provides standardized context sharing between AI models and application components
 * @version 1.0.0
 */

// Types for MCP context
interface MCPContext {
  context_id?: string;
  operation?: string;
  parameters?: Record<string, any>;
  result?: Record<string, any> | null;
  status?: string;
  timestamp?: number;
  error?: string | null;
  model_id?: string;
  metadata?: Record<string, any>;
}

// Handle HTTP request
serve(async (req) => {
  // Default response
  const response = {
    context_id: crypto.randomUUID(),
    operation: "connect",
    status: "success",
    timestamp: Date.now(),
    model_id: null,
    result: { 
      message: "MCP connection successful" 
    }
  };

  // If this is a POST request, process the body
  if (req.method === "POST") {
    try {
      const body = await req.json();
      
      if (body.modelId) {
        response.model_id = body.modelId;
        response.result.message = `Connected to model: ${body.modelId}`;
      }
      
      if (body.context) {
        // Merge context fields if provided
        if (body.context.context_id) response.context_id = body.context.context_id;
        if (body.context.operation) response.operation = body.context.operation;
      }
    } catch (e) {
      response.status = "error";
      response.result = { message: "Error processing request" };
    }
  }

  // Return JSON response
  return new Response(
    JSON.stringify(response),
    { headers: { 'Content-Type': 'application/json' } }
  );
}); 