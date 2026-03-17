export type OrchestrationSummary = {
    startedAt: string;
    endedAt: string;
    adapters: {
        name: string;
        records: number;
        errors: string[];
    }[];
    embeddingTriggered: boolean;
    totalRecords: number;
    totalErrors: number;
};
export declare function orchestrate(triggerSource?: string): Promise<OrchestrationSummary>;
