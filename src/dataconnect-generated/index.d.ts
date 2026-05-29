import { ConnectorConfig, DataConnect, QueryRef, QueryPromise, ExecuteQueryOptions, MutationRef, MutationPromise } from 'firebase/data-connect';

export const connectorConfig: ConnectorConfig;

export type TimestampString = string;
export type UUIDString = string;
export type Int64String = string;
export type DateString = string;




export interface CompleteJobData {
  videoJob_updateMany: number;
}

export interface CompleteJobVariables {
  id: UUIDString;
  resultJson: string;
  title?: string | null;
}

export interface CreateVideoJobData {
  videoJob_insert: VideoJob_Key;
}

export interface CreateVideoJobVariables {
  videoUrl: string;
  source: string;
  taskType: string;
}

export interface DeleteJobEmbeddingsData {
  videoEmbedding_deleteMany: number;
}

export interface DeleteJobEmbeddingsVariables {
  jobId: UUIDString;
}

export interface FailJobData {
  videoJob_updateMany: number;
}

export interface FailJobVariables {
  id: UUIDString;
  error: string;
}

export interface GetJobData {
  videoJobs: ({
    id: UUIDString;
    videoUrl: string;
    source: string;
    taskType: string;
    status: string;
    executedAgents: string[];
    resultJson?: string | null;
    error?: string | null;
    title?: string | null;
    createdAt: TimestampString;
    updatedAt: TimestampString;
  } & VideoJob_Key)[];
}

export interface GetJobEmbeddingsData {
  videoEmbeddings: ({
    id: UUIDString;
    segmentType: string;
    segmentIndex: number;
    content: string;
    createdAt: TimestampString;
  } & VideoEmbedding_Key)[];
}

export interface GetJobEmbeddingsVariables {
  jobId: UUIDString;
}

export interface GetJobEventsData {
  jobEvents: ({
    id: UUIDString;
    eventType: string;
    agent?: string | null;
    details?: string | null;
    timestamp: TimestampString;
  } & JobEvent_Key)[];
}

export interface GetJobEventsVariables {
  jobId: UUIDString;
}

export interface GetJobVariables {
  id: UUIDString;
}

export interface JobEvent_Key {
  id: UUIDString;
  __typename?: 'JobEvent_Key';
}

export interface ListEmbeddingsData {
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
  } & VideoEmbedding_Key)[];
}

export interface ListEmbeddingsVariables {
  limit?: number | null;
}

export interface ListJobsData {
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

export interface ListJobsVariables {
  limit?: number | null;
}

export interface RecordJobEventData {
  jobEvent_insert: JobEvent_Key;
}

export interface RecordJobEventVariables {
  jobId: UUIDString;
  eventType: string;
  agent?: string | null;
  details?: string | null;
}

export interface UpdateJobStatusData {
  videoJob_updateMany: number;
}

export interface UpdateJobStatusVariables {
  id: UUIDString;
  status: string;
  executedAgents?: string[] | null;
}

export interface VideoEmbedding_Key {
  id: UUIDString;
  __typename?: 'VideoEmbedding_Key';
}

export interface VideoJob_Key {
  id: UUIDString;
  __typename?: 'VideoJob_Key';
}

interface CreateVideoJobRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateVideoJobVariables): MutationRef<CreateVideoJobData, CreateVideoJobVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: CreateVideoJobVariables): MutationRef<CreateVideoJobData, CreateVideoJobVariables>;
  operationName: string;
}
export const createVideoJobRef: CreateVideoJobRef;

export function createVideoJob(vars: CreateVideoJobVariables): MutationPromise<CreateVideoJobData, CreateVideoJobVariables>;
export function createVideoJob(dc: DataConnect, vars: CreateVideoJobVariables): MutationPromise<CreateVideoJobData, CreateVideoJobVariables>;

interface UpdateJobStatusRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: UpdateJobStatusVariables): MutationRef<UpdateJobStatusData, UpdateJobStatusVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: UpdateJobStatusVariables): MutationRef<UpdateJobStatusData, UpdateJobStatusVariables>;
  operationName: string;
}
export const updateJobStatusRef: UpdateJobStatusRef;

export function updateJobStatus(vars: UpdateJobStatusVariables): MutationPromise<UpdateJobStatusData, UpdateJobStatusVariables>;
export function updateJobStatus(dc: DataConnect, vars: UpdateJobStatusVariables): MutationPromise<UpdateJobStatusData, UpdateJobStatusVariables>;

interface CompleteJobRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: CompleteJobVariables): MutationRef<CompleteJobData, CompleteJobVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: CompleteJobVariables): MutationRef<CompleteJobData, CompleteJobVariables>;
  operationName: string;
}
export const completeJobRef: CompleteJobRef;

export function completeJob(vars: CompleteJobVariables): MutationPromise<CompleteJobData, CompleteJobVariables>;
export function completeJob(dc: DataConnect, vars: CompleteJobVariables): MutationPromise<CompleteJobData, CompleteJobVariables>;

interface FailJobRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: FailJobVariables): MutationRef<FailJobData, FailJobVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: FailJobVariables): MutationRef<FailJobData, FailJobVariables>;
  operationName: string;
}
export const failJobRef: FailJobRef;

export function failJob(vars: FailJobVariables): MutationPromise<FailJobData, FailJobVariables>;
export function failJob(dc: DataConnect, vars: FailJobVariables): MutationPromise<FailJobData, FailJobVariables>;

interface RecordJobEventRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: RecordJobEventVariables): MutationRef<RecordJobEventData, RecordJobEventVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: RecordJobEventVariables): MutationRef<RecordJobEventData, RecordJobEventVariables>;
  operationName: string;
}
export const recordJobEventRef: RecordJobEventRef;

export function recordJobEvent(vars: RecordJobEventVariables): MutationPromise<RecordJobEventData, RecordJobEventVariables>;
export function recordJobEvent(dc: DataConnect, vars: RecordJobEventVariables): MutationPromise<RecordJobEventData, RecordJobEventVariables>;

interface GetJobRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetJobVariables): QueryRef<GetJobData, GetJobVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: GetJobVariables): QueryRef<GetJobData, GetJobVariables>;
  operationName: string;
}
export const getJobRef: GetJobRef;

export function getJob(vars: GetJobVariables, options?: ExecuteQueryOptions): QueryPromise<GetJobData, GetJobVariables>;
export function getJob(dc: DataConnect, vars: GetJobVariables, options?: ExecuteQueryOptions): QueryPromise<GetJobData, GetJobVariables>;

interface ListJobsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars?: ListJobsVariables): QueryRef<ListJobsData, ListJobsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars?: ListJobsVariables): QueryRef<ListJobsData, ListJobsVariables>;
  operationName: string;
}
export const listJobsRef: ListJobsRef;

export function listJobs(vars?: ListJobsVariables, options?: ExecuteQueryOptions): QueryPromise<ListJobsData, ListJobsVariables>;
export function listJobs(dc: DataConnect, vars?: ListJobsVariables, options?: ExecuteQueryOptions): QueryPromise<ListJobsData, ListJobsVariables>;

interface GetJobEventsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetJobEventsVariables): QueryRef<GetJobEventsData, GetJobEventsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: GetJobEventsVariables): QueryRef<GetJobEventsData, GetJobEventsVariables>;
  operationName: string;
}
export const getJobEventsRef: GetJobEventsRef;

export function getJobEvents(vars: GetJobEventsVariables, options?: ExecuteQueryOptions): QueryPromise<GetJobEventsData, GetJobEventsVariables>;
export function getJobEvents(dc: DataConnect, vars: GetJobEventsVariables, options?: ExecuteQueryOptions): QueryPromise<GetJobEventsData, GetJobEventsVariables>;

interface ListEmbeddingsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars?: ListEmbeddingsVariables): QueryRef<ListEmbeddingsData, ListEmbeddingsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars?: ListEmbeddingsVariables): QueryRef<ListEmbeddingsData, ListEmbeddingsVariables>;
  operationName: string;
}
export const listEmbeddingsRef: ListEmbeddingsRef;

export function listEmbeddings(vars?: ListEmbeddingsVariables, options?: ExecuteQueryOptions): QueryPromise<ListEmbeddingsData, ListEmbeddingsVariables>;
export function listEmbeddings(dc: DataConnect, vars?: ListEmbeddingsVariables, options?: ExecuteQueryOptions): QueryPromise<ListEmbeddingsData, ListEmbeddingsVariables>;

interface GetJobEmbeddingsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetJobEmbeddingsVariables): QueryRef<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: GetJobEmbeddingsVariables): QueryRef<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;
  operationName: string;
}
export const getJobEmbeddingsRef: GetJobEmbeddingsRef;

export function getJobEmbeddings(vars: GetJobEmbeddingsVariables, options?: ExecuteQueryOptions): QueryPromise<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;
export function getJobEmbeddings(dc: DataConnect, vars: GetJobEmbeddingsVariables, options?: ExecuteQueryOptions): QueryPromise<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;

interface DeleteJobEmbeddingsRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: DeleteJobEmbeddingsVariables): MutationRef<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: DeleteJobEmbeddingsVariables): MutationRef<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;
  operationName: string;
}
export const deleteJobEmbeddingsRef: DeleteJobEmbeddingsRef;

export function deleteJobEmbeddings(vars: DeleteJobEmbeddingsVariables): MutationPromise<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;
export function deleteJobEmbeddings(dc: DataConnect, vars: DeleteJobEmbeddingsVariables): MutationPromise<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;

