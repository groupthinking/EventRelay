import { streamText } from 'ai'

const model = process.env.AI_GATEWAY_MODEL || 'openai/gpt-5.5'

const result = streamText({
  model,
  prompt: 'Explain quantum computing in simple terms.',
})

for await (const chunk of result.textStream) {
  process.stdout.write(chunk)
}
