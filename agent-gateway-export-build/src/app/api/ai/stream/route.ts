import { streamText } from 'ai'

export const runtime = 'edge'

export async function POST(request: Request) {
  const { prompt, model = process.env.AI_GATEWAY_MODEL || 'openai/gpt-5.5' } = await request.json()

  if (!prompt || typeof prompt !== 'string') {
    return Response.json(
      { error: { code: 'schema_invalid', message: 'Prompt is required.' } },
      { status: 400 },
    )
  }

  const result = streamText({ model, prompt })
  return result.toTextStreamResponse()
}
