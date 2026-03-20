import { ConnectorConfig, DataConnect, QueryRef, QueryPromise, MutationRef, MutationPromise } from 'firebase/data-connect';

export const connectorConfig: ConnectorConfig;

export type TimestampString = string;
export type UUIDString = string;
export type Int64String = string;
export type DateString = string;




export interface CreateExampleJobData {
  videoJob_insert: VideoJob_Key;
}

export interface CreateExampleJobVariables {
  videoUrl: string;
  source: string;
  taskType: string;
}

export interface DeleteExampleEventData {
  jobEvent_delete?: JobEvent_Key | null;
}

export interface DeleteExampleEventVariables {
  id: UUIDString;
}

export interface GetVideoJobData {
  videoJob?: {
    id: UUIDString;
    videoUrl: string;
    source: string;
    taskType: string;
    status: string;
    executedAgents: string[];
    resultJson?: string | null;
    error?: string | null;
    title?: string | null;
    duration?: number | null;
    fileSize?: number | null;
    createdAt: TimestampString;
    updatedAt: TimestampString;
  } & VideoJob_Key;
}

export interface GetVideoJobVariables {
  id: UUIDString;
}

export interface JobEvent_Key {
  id: UUIDString;
  __typename?: 'JobEvent_Key';
}

export interface ListFailedJobsData {
  videoJobs: ({
    id: UUIDString;
    videoUrl: string;
    error?: string | null;
    executedAgents: string[];
    updatedAt: TimestampString;
  } & VideoJob_Key)[];
}

export interface ListJobEventsData {
  jobEvents: ({
    id: UUIDString;
    eventType: string;
    agent?: string | null;
    details?: string | null;
    timestamp: TimestampString;
  } & JobEvent_Key)[];
}

export interface ListJobEventsVariables {
  jobId: UUIDString;
}

export interface ListVideoEmbeddingsData {
  videoEmbeddings: ({
    id: UUIDString;
    segmentType: string;
    segmentIndex: number;
    content: string;
    job: {
      id: UUIDString;
      title?: string | null;
      videoUrl: string;
    } & VideoJob_Key;
      createdAt: TimestampString;
  } & VideoEmbedding_Key)[];
}

export interface ListVideoEmbeddingsVariables {
  limit?: number | null;
}

export interface ListVideoJobsData {
  videoJobs: ({
    id: UUIDString;
    videoUrl: string;
    source: string;
    taskType: string;
    status: string;
    title?: string | null;
    createdAt: TimestampString;
    updatedAt: TimestampString;
  } & VideoJob_Key)[];
}

export interface RecordExampleEventData {
  jobEvent_insert: JobEvent_Key;
}

export interface RecordExampleEventVariables {
  jobId: UUIDString;
  eventType: string;
  agent?: string | null;
  details?: string | null;
}

export interface VideoEmbedding_Key {
  id: UUIDString;
  __typename?: 'VideoEmbedding_Key';
}

export interface VideoJob_Key {
  id: UUIDString;
  __typename?: 'VideoJob_Key';
}

interface ListVideoJobsRef {
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<ListVideoJobsData, undefined>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect): QueryRef<ListVideoJobsData, undefined>;
  operationName: string;
}
export const listVideoJobsRef: ListVideoJobsRef;

export function listVideoJobs(): QueryPromise<ListVideoJobsData, undefined>;
export function listVideoJobs(dc: DataConnect): QueryPromise<ListVideoJobsData, undefined>;

interface GetVideoJobRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetVideoJobVariables): QueryRef<GetVideoJobData, GetVideoJobVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: GetVideoJobVariables): QueryRef<GetVideoJobData, GetVideoJobVariables>;
  operationName: string;
}
export const getVideoJobRef: GetVideoJobRef;

export function getVideoJob(vars: GetVideoJobVariables): QueryPromise<GetVideoJobData, GetVideoJobVariables>;
export function getVideoJob(dc: DataConnect, vars: GetVideoJobVariables): QueryPromise<GetVideoJobData, GetVideoJobVariables>;

interface ListJobEventsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: ListJobEventsVariables): QueryRef<ListJobEventsData, ListJobEventsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: ListJobEventsVariables): QueryRef<ListJobEventsData, ListJobEventsVariables>;
  operationName: string;
}
export const listJobEventsRef: ListJobEventsRef;

export function listJobEvents(vars: ListJobEventsVariables): QueryPromise<ListJobEventsData, ListJobEventsVariables>;
export function listJobEvents(dc: DataConnect, vars: ListJobEventsVariables): QueryPromise<ListJobEventsData, ListJobEventsVariables>;

interface ListVideoEmbeddingsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars?: ListVideoEmbeddingsVariables): QueryRef<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars?: ListVideoEmbeddingsVariables): QueryRef<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;
  operationName: string;
}
export const listVideoEmbeddingsRef: ListVideoEmbeddingsRef;

export function listVideoEmbeddings(vars?: ListVideoEmbeddingsVariables): QueryPromise<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;
export function listVideoEmbeddings(dc: DataConnect, vars?: ListVideoEmbeddingsVariables): QueryPromise<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;

interface ListFailedJobsRef {
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<ListFailedJobsData, undefined>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect): QueryRef<ListFailedJobsData, undefined>;
  operationName: string;
}
export const listFailedJobsRef: ListFailedJobsRef;

export function listFailedJobs(): QueryPromise<ListFailedJobsData, undefined>;
export function listFailedJobs(dc: DataConnect): QueryPromise<ListFailedJobsData, undefined>;

interface CreateExampleJobRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateExampleJobVariables): MutationRef<CreateExampleJobData, CreateExampleJobVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: CreateExampleJobVariables): MutationRef<CreateExampleJobData, CreateExampleJobVariables>;
  operationName: string;
}
export const createExampleJobRef: CreateExampleJobRef;

export function createExampleJob(vars: CreateExampleJobVariables): MutationPromise<CreateExampleJobData, CreateExampleJobVariables>;
export function createExampleJob(dc: DataConnect, vars: CreateExampleJobVariables): MutationPromise<CreateExampleJobData, CreateExampleJobVariables>;

interface RecordExampleEventRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: RecordExampleEventVariables): MutationRef<RecordExampleEventData, RecordExampleEventVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: RecordExampleEventVariables): MutationRef<RecordExampleEventData, RecordExampleEventVariables>;
  operationName: string;
}
export const recordExampleEventRef: RecordExampleEventRef;

export function recordExampleEvent(vars: RecordExampleEventVariables): MutationPromise<RecordExampleEventData, RecordExampleEventVariables>;
export function recordExampleEvent(dc: DataConnect, vars: RecordExampleEventVariables): MutationPromise<RecordExampleEventData, RecordExampleEventVariables>;

interface DeleteExampleEventRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: DeleteExampleEventVariables): MutationRef<DeleteExampleEventData, DeleteExampleEventVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: DeleteExampleEventVariables): MutationRef<DeleteExampleEventData, DeleteExampleEventVariables>;
  operationName: string;
}
export const deleteExampleEventRef: DeleteExampleEventRef;

export function deleteExampleEvent(vars: DeleteExampleEventVariables): MutationPromise<DeleteExampleEventData, DeleteExampleEventVariables>;
export function deleteExampleEvent(dc: DataConnect, vars: DeleteExampleEventVariables): MutationPromise<DeleteExampleEventData, DeleteExampleEventVariables>;

