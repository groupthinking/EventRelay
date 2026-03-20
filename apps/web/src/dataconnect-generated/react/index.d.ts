import { ListVideoJobsData, GetVideoJobData, GetVideoJobVariables, ListJobEventsData, ListJobEventsVariables, ListVideoEmbeddingsData, ListVideoEmbeddingsVariables, ListFailedJobsData, CreateExampleJobData, CreateExampleJobVariables, RecordExampleEventData, RecordExampleEventVariables, DeleteExampleEventData, DeleteExampleEventVariables } from '../';
import { UseDataConnectQueryResult, useDataConnectQueryOptions, UseDataConnectMutationResult, useDataConnectMutationOptions} from '@tanstack-query-firebase/react/data-connect';
import { UseQueryResult, UseMutationResult} from '@tanstack/react-query';
import { DataConnect } from 'firebase/data-connect';
import { FirebaseError } from 'firebase/app';


export function useListVideoJobs(options?: useDataConnectQueryOptions<ListVideoJobsData>): UseDataConnectQueryResult<ListVideoJobsData, undefined>;
export function useListVideoJobs(dc: DataConnect, options?: useDataConnectQueryOptions<ListVideoJobsData>): UseDataConnectQueryResult<ListVideoJobsData, undefined>;

export function useGetVideoJob(vars: GetVideoJobVariables, options?: useDataConnectQueryOptions<GetVideoJobData>): UseDataConnectQueryResult<GetVideoJobData, GetVideoJobVariables>;
export function useGetVideoJob(dc: DataConnect, vars: GetVideoJobVariables, options?: useDataConnectQueryOptions<GetVideoJobData>): UseDataConnectQueryResult<GetVideoJobData, GetVideoJobVariables>;

export function useListJobEvents(vars: ListJobEventsVariables, options?: useDataConnectQueryOptions<ListJobEventsData>): UseDataConnectQueryResult<ListJobEventsData, ListJobEventsVariables>;
export function useListJobEvents(dc: DataConnect, vars: ListJobEventsVariables, options?: useDataConnectQueryOptions<ListJobEventsData>): UseDataConnectQueryResult<ListJobEventsData, ListJobEventsVariables>;

export function useListVideoEmbeddings(vars?: ListVideoEmbeddingsVariables, options?: useDataConnectQueryOptions<ListVideoEmbeddingsData>): UseDataConnectQueryResult<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;
export function useListVideoEmbeddings(dc: DataConnect, vars?: ListVideoEmbeddingsVariables, options?: useDataConnectQueryOptions<ListVideoEmbeddingsData>): UseDataConnectQueryResult<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;

export function useListFailedJobs(options?: useDataConnectQueryOptions<ListFailedJobsData>): UseDataConnectQueryResult<ListFailedJobsData, undefined>;
export function useListFailedJobs(dc: DataConnect, options?: useDataConnectQueryOptions<ListFailedJobsData>): UseDataConnectQueryResult<ListFailedJobsData, undefined>;

export function useCreateExampleJob(options?: useDataConnectMutationOptions<CreateExampleJobData, FirebaseError, CreateExampleJobVariables>): UseDataConnectMutationResult<CreateExampleJobData, CreateExampleJobVariables>;
export function useCreateExampleJob(dc: DataConnect, options?: useDataConnectMutationOptions<CreateExampleJobData, FirebaseError, CreateExampleJobVariables>): UseDataConnectMutationResult<CreateExampleJobData, CreateExampleJobVariables>;

export function useRecordExampleEvent(options?: useDataConnectMutationOptions<RecordExampleEventData, FirebaseError, RecordExampleEventVariables>): UseDataConnectMutationResult<RecordExampleEventData, RecordExampleEventVariables>;
export function useRecordExampleEvent(dc: DataConnect, options?: useDataConnectMutationOptions<RecordExampleEventData, FirebaseError, RecordExampleEventVariables>): UseDataConnectMutationResult<RecordExampleEventData, RecordExampleEventVariables>;

export function useDeleteExampleEvent(options?: useDataConnectMutationOptions<DeleteExampleEventData, FirebaseError, DeleteExampleEventVariables>): UseDataConnectMutationResult<DeleteExampleEventData, DeleteExampleEventVariables>;
export function useDeleteExampleEvent(dc: DataConnect, options?: useDataConnectMutationOptions<DeleteExampleEventData, FirebaseError, DeleteExampleEventVariables>): UseDataConnectMutationResult<DeleteExampleEventData, DeleteExampleEventVariables>;
