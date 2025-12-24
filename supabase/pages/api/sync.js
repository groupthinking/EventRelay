import { syncMemoryLogsToSupabase } from '../../lib/mcp_enhancer';
import { createMcpContext, propagateMcp, logMcp } from '../../lib/mcp';

/**
 * API endpoint to sync memory logs to Supabase
 * Useful for ensuring all logs are persisted
 */
export default async function handler(req, res) {
  // Create MCP context for this request
  const mcp_context = createMcpContext('api_sync_logs', 'next-api', { 
    method: req.method,
    query: req.query
  });

  try {
    // Only allow POST requests
    if (req.method !== 'POST') {
      logMcp(propagateMcp(mcp_context, { 
        status: 'error', 
        error: 'Method not allowed' 
      }));
      return res.status(405).json({ error: 'Method not allowed' });
    }
    
    // Perform the sync
    logMcp(propagateMcp(mcp_context, { status: 'syncing' }));
    const result = await syncMemoryLogsToSupabase();
    
    // Log the result
    logMcp(propagateMcp(mcp_context, { 
      status: 'complete',
      syncedCount: result.count 
    }), result);
    
    return res.status(200).json({ 
      success: true, 
      message: `Synced ${result.count} logs to Supabase`,
      count: result.count
    });
  } catch (e) {
    // Log any unexpected errors
    logMcp(propagateMcp(mcp_context, { 
      status: 'exception', 
      error: e.message 
    }));
    return res.status(500).json({ error: e.message });
  }
} 