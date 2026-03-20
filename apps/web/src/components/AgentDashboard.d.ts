import type { AgentExecution } from '@/lib/types';
interface AgentDashboardProps {
    executions: AgentExecution[];
    loading?: boolean;
    className?: string;
}
export default function AgentDashboard({ executions, loading, className }: AgentDashboardProps): import("react").JSX.Element | null;
export {};
