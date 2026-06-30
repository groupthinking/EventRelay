"use strict";
// Follow Supabase Edge Function format
// https://supabase.com/docs/guides/functions/quickstart
Object.defineProperty(exports, "__esModule", { value: true });
// Import Supabase Edge Function runtime
const server_ts_1 = require("https://deno.land/std@0.168.0/http/server.ts");
// Handle HTTP request
(0, server_ts_1.serve)(async (req) => {
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
                if (body.context.context_id)
                    response.context_id = body.context.context_id;
                if (body.context.operation)
                    response.operation = body.context.operation;
            }
        }
        catch (e) {
            response.status = "error";
            response.result = { message: "Error processing request" };
        }
    }
    // Return JSON response
    return new Response(JSON.stringify(response), { headers: { 'Content-Type': 'application/json' } });
});
//# sourceMappingURL=index.js.map