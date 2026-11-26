import { NextRequest } from 'next/server'
import { ExportFailure, safeExportFilename } from '@/lib/agent-substrate/schema'
import { exportAgentSubstrateWorkflow } from '@/workflows/agentExport'

function errorResponse(error: unknown) {
  if (error instanceof ExportFailure) {
    return Response.json(
      { error: { code: error.code, message: error.message } },
      { status: error.status },
    )
  }

  console.error('agent_export_unhandled_error', error)
  return Response.json(
    { error: { code: 'download_client_error', message: 'Export failed. Please try again.' } },
    { status: 500 },
  )
}

async function authorizeExport(_request: NextRequest, agentId: string) {
  // Replace this with your real session, workspace, and agent ACL checks.
  if (!agentId) throw new ExportFailure('not_found', 'No agent was selected.', 404)
  return { ok: true }
}

export async function GET(request: NextRequest, context: { params: Promise<{ agentId: string }> }) {
  try {
    const { agentId } = await context.params
    await authorizeExport(request, agentId)

    const payload = await exportAgentSubstrateWorkflow(agentId)
    const body = JSON.stringify(payload, null, 2)
    const filename = safeExportFilename(payload.name, payload.exportedAt)

    return new Response(body, {
      status: 200,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Cache-Control': 'no-store',
      },
    })
  } catch (error) {
    return errorResponse(error)
  }
}
