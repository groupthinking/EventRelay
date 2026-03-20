import type { AgentExecution, ExtractedEvent } from '@/lib/types';
interface ResultsViewerProps {
    executions: AgentExecution[];
    events: ExtractedEvent[];
    className?: string;
}
export default function ResultsViewer({ executions, events, className }: ResultsViewerProps): import("react").JSX.Element | null;
export {};
