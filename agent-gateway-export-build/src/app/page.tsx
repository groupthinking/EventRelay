import { InspectorSidebar } from '@/components/InspectorSidebar'

export default function Page() {
  return (
    <main className="grid min-h-screen grid-cols-[1fr_380px] bg-neutral-50 text-neutral-950">
      <section className="p-8">
        <h1 className="text-2xl font-semibold">Agent Substrate</h1>
        <p className="mt-2 max-w-2xl text-neutral-600">
          Demo surface for the full-stack agent export flow. Replace the demo agent with your selected runtime agent.
        </p>
      </section>
      <InspectorSidebar
        selectedAgent={{
          id: 'agent-demo',
          name: 'Demo Agent',
          description: 'Example selected agent with knowledge, connections, and event history.',
        }}
      />
    </main>
  )
}
