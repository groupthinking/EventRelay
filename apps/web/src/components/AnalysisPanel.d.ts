interface AnalysisPanelProps {
    videoId: string;
    videoUrl: string;
    initialContext?: string;
    onClose?: () => void;
}
export default function AnalysisPanel({ videoId, videoUrl, initialContext, onClose }: AnalysisPanelProps): import("react").JSX.Element;
export {};
