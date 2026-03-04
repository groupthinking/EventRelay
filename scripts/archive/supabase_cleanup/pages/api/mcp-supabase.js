import { createMcpContext, propagateMcp } from '../../lib/mcp';
import { logMcpToSupabase } from '../../lib/mcp_enhancer';
import SupabaseMcpClient from '../../lib/supabase_mcp_client';
import { runMcpSupabaseWorkflow, queryProjects, batchOperationWithMcp } from '../../lib/supabase_mcp_examples';

/**
 * API endpoint for direct Supabase MCP interaction
 * 
 * This endpoint demonstrates different patterns of using SupabaseMcpClient:
 * - Direct operation mode: performs a single database operation with MCP context
 * - Workflow mode: runs a multi-step workflow with full context propagation
 * - Batch mode: processes multiple records in sequence with MCP tracing
 */
export default async function handler(req, res) {
  // Create MCP context for this API request
  const apiContext = createMcpContext('api_mcp_supabase', 'next-api', { 
    method: req.method,
    query: req.query,
    body: req.method === 'POST' ? req.body : null
  });

  try {
    // Update context status
    await logMcpToSupabase(propagateMcp(apiContext, { status: 'processing' }));

    // Only allow POST requests
    if (req.method !== 'POST') {
      await logMcpToSupabase(propagateMcp(apiContext, { 
        status: 'error', 
        error: 'Method not allowed' 
      }));
      return res.status(405).json({ error: 'Method not allowed' });
    }
    
    const { mode = 'direct', action, table, data } = req.body;
    
    // Handle different operation modes
    switch (mode) {
      case 'direct': {
        // Direct operation mode: perform a single database operation
        const client = new SupabaseMcpClient({
          source: 'api-direct',
          parentContext: apiContext
        });
        
        let result;
        
        switch (action) {
          case 'query':
            result = await client.query(table, {
              filters: data?.filters || {},
              select: data?.select || '*',
              limit: data?.limit || 50,
              offset: data?.offset || 0,
              order: data?.order || null
            });
            break;
            
          case 'insert':
            result = await client.insert(table, data, {
              returning: 'representation'
            });
            break;
            
          case 'update':
            if (!data?.match) {
              await logMcpToSupabase(propagateMcp(apiContext, { 
                status: 'error', 
                error: 'Match criteria required for update' 
              }));
              return res.status(400).json({ error: 'Match criteria required for update' });
            }
            
            result = await client.update(table, data.values, {
              match: data.match,
              returning: 'representation'
            });
            break;
            
          case 'delete':
            if (!data?.match) {
              await logMcpToSupabase(propagateMcp(apiContext, { 
                status: 'error', 
                error: 'Match criteria required for delete' 
              }));
              return res.status(400).json({ error: 'Match criteria required for delete' });
            }
            
            result = await client.delete(table, {
              match: data.match,
              returning: 'representation'
            });
            break;
            
          case 'rpc':
            if (!data?.function) {
              await logMcpToSupabase(propagateMcp(apiContext, { 
                status: 'error', 
                error: 'Function name required for RPC' 
              }));
              return res.status(400).json({ error: 'Function name required for RPC' });
            }
            
            result = await client.rpc(data.function, data.params || {});
            break;
            
          default:
            await logMcpToSupabase(propagateMcp(apiContext, { 
              status: 'error', 
              error: `Unknown action: ${action}` 
            }));
            return res.status(400).json({ error: `Unknown action: ${action}` });
        }
        
        // Update API context with operation result
        await logMcpToSupabase(propagateMcp(apiContext, { 
          status: 'complete', 
          operation: action,
          table,
          resultStatus: result.error ? 'error' : 'success'
        }));
        
        return res.status(200).json({
          success: !result.error,
          data: result.data,
          error: result.error,
          contextId: result.context.contextId
        });
      }
      
      case 'workflow': {
        // Run the workflow demonstration
        const result = await runMcpSupabaseWorkflow();
        
        // Update API context with workflow result
        await logMcpToSupabase(propagateMcp(apiContext, { 
          status: 'complete', 
          workflowSuccess: result.success,
          workflowContextId: result.contexts?.workflow?.contextId
        }));
        
        return res.status(200).json({
          success: result.success,
          data: result.data || null,
          error: result.error || null,
          contextId: result.context?.contextId || result.contexts?.workflow?.contextId
        });
      }
      
      case 'batch': {
        // Batch operation mode
        if (!Array.isArray(data)) {
          await logMcpToSupabase(propagateMcp(apiContext, { 
            status: 'error', 
            error: 'Batch mode requires an array of records' 
          }));
          return res.status(400).json({ error: 'Batch mode requires an array of records' });
        }
        
        const result = await batchOperationWithMcp(data);
        
        // Update API context with batch operation result
        await logMcpToSupabase(propagateMcp(apiContext, { 
          status: 'complete', 
          batchSuccess: result.success,
          successCount: result.results.filter(r => !r.error).length,
          errorCount: result.results.filter(r => r.error).length,
          batchContextId: result.finalContext.contextId
        }));
        
        return res.status(200).json({
          success: result.success,
          results: result.results,
          contextId: result.finalContext.contextId
        });
      }
      
      case 'query': {
        // Simple query mode - for convenience
        const result = await queryProjects(data || {});
        
        // Update API context with query result
        await logMcpToSupabase(propagateMcp(apiContext, { 
          status: 'complete', 
          querySuccess: result.success,
          resultCount: result.data?.length || 0,
          queryContextId: result.context.contextId
        }));
        
        return res.status(200).json({
          success: result.success,
          data: result.data,
          error: result.error,
          contextId: result.context.contextId
        });
      }
      
      default:
        await logMcpToSupabase(propagateMcp(apiContext, { 
          status: 'error', 
          error: `Unknown mode: ${mode}` 
        }));
        return res.status(400).json({ error: `Unknown mode: ${mode}` });
    }
  } catch (e) {
    // Log any unexpected errors
    console.error('API exception:', e);
    await logMcpToSupabase(propagateMcp(apiContext, { 
      status: 'exception', 
      error: e.message 
    }));
    return res.status(500).json({ error: e.message });
  }
} 