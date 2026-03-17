import type { ExtractedEvent } from '@/lib/types';
interface EventListProps {
    events: ExtractedEvent[];
    loading?: boolean;
    onExtract?: () => void;
    className?: string;
}
export default function EventList({ events, loading, onExtract, className }: EventListProps): import("react").JSX.Element;
export {};
