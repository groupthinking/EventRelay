# Generated TypeScript README
This README will guide you through the process of using the generated JavaScript SDK package for the connector `example`. It will also provide examples on how to use your generated SDK to call your Data Connect queries and mutations.

**If you're looking for the `React README`, you can find it at [`dataconnect-generated/react/README.md`](./react/README.md)**

***NOTE:** This README is generated alongside the generated SDK. If you make changes to this file, they will be overwritten when the SDK is regenerated.*

# Table of Contents
- [**Overview**](#generated-javascript-readme)
- [**Accessing the connector**](#accessing-the-connector)
  - [*Connecting to the local Emulator*](#connecting-to-the-local-emulator)
- [**Queries**](#queries)
  - [*ListVideoJobs*](#listvideojobs)
  - [*GetVideoJob*](#getvideojob)
  - [*ListJobEvents*](#listjobevents)
  - [*ListVideoEmbeddings*](#listvideoembeddings)
  - [*ListFailedJobs*](#listfailedjobs)
- [**Mutations**](#mutations)
  - [*CreateExampleJob*](#createexamplejob)
  - [*RecordExampleEvent*](#recordexampleevent)
  - [*DeleteExampleEvent*](#deleteexampleevent)

# Accessing the connector
A connector is a collection of Queries and Mutations. One SDK is generated for each connector - this SDK is generated for the connector `example`. You can find more information about connectors in the [Data Connect documentation](https://firebase.google.com/docs/data-connect#how-does).

You can use this generated SDK by importing from the package `@dataconnect/generated` as shown below. Both CommonJS and ESM imports are supported.

You can also follow the instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#set-client).

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@dataconnect/generated';

const dataConnect = getDataConnect(connectorConfig);
```

## Connecting to the local Emulator
By default, the connector will connect to the production service.

To connect to the emulator, you can use the following code.
You can also follow the emulator instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#instrument-clients).

```typescript
import { connectDataConnectEmulator, getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@dataconnect/generated';

const dataConnect = getDataConnect(connectorConfig);
connectDataConnectEmulator(dataConnect, 'localhost', 9399);
```

After it's initialized, you can call your Data Connect [queries](#queries) and [mutations](#mutations) from your generated SDK.

# Queries

There are two ways to execute a Data Connect Query using the generated Web SDK:
- Using a Query Reference function, which returns a `QueryRef`
  - The `QueryRef` can be used as an argument to `executeQuery()`, which will execute the Query and return a `QueryPromise`
- Using an action shortcut function, which returns a `QueryPromise`
  - Calling the action shortcut function will execute the Query and return a `QueryPromise`

The following is true for both the action shortcut function and the `QueryRef` function:
- The `QueryPromise` returned will resolve to the result of the Query once it has finished executing
- If the Query accepts arguments, both the action shortcut function and the `QueryRef` function accept a single argument: an object that contains all the required variables (and the optional variables) for the Query
- Both functions can be called with or without passing in a `DataConnect` instance as an argument. If no `DataConnect` argument is passed in, then the generated SDK will call `getDataConnect(connectorConfig)` behind the scenes for you.

Below are examples of how to use the `example` connector's generated functions to execute each query. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-queries).

## ListVideoJobs
You can execute the `ListVideoJobs` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listVideoJobs(): QueryPromise<ListVideoJobsData, undefined>;

interface ListVideoJobsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<ListVideoJobsData, undefined>;
}
export const listVideoJobsRef: ListVideoJobsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listVideoJobs(dc: DataConnect): QueryPromise<ListVideoJobsData, undefined>;

interface ListVideoJobsRef {
  ...
  (dc: DataConnect): QueryRef<ListVideoJobsData, undefined>;
}
export const listVideoJobsRef: ListVideoJobsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listVideoJobsRef:
```typescript
const name = listVideoJobsRef.operationName;
console.log(name);
```

### Variables
The `ListVideoJobs` query has no variables.
### Return Type
Recall that executing the `ListVideoJobs` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListVideoJobsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
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
```
### Using `ListVideoJobs`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listVideoJobs } from '@dataconnect/generated';


// Call the `listVideoJobs()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listVideoJobs();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listVideoJobs(dataConnect);

console.log(data.videoJobs);

// Or, you can use the `Promise` API.
listVideoJobs().then((response) => {
  const data = response.data;
  console.log(data.videoJobs);
});
```

### Using `ListVideoJobs`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listVideoJobsRef } from '@dataconnect/generated';


// Call the `listVideoJobsRef()` function to get a reference to the query.
const ref = listVideoJobsRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listVideoJobsRef(dataConnect);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.videoJobs);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJobs);
});
```

## GetVideoJob
You can execute the `GetVideoJob` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
getVideoJob(vars: GetVideoJobVariables): QueryPromise<GetVideoJobData, GetVideoJobVariables>;

interface GetVideoJobRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetVideoJobVariables): QueryRef<GetVideoJobData, GetVideoJobVariables>;
}
export const getVideoJobRef: GetVideoJobRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
getVideoJob(dc: DataConnect, vars: GetVideoJobVariables): QueryPromise<GetVideoJobData, GetVideoJobVariables>;

interface GetVideoJobRef {
  ...
  (dc: DataConnect, vars: GetVideoJobVariables): QueryRef<GetVideoJobData, GetVideoJobVariables>;
}
export const getVideoJobRef: GetVideoJobRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the getVideoJobRef:
```typescript
const name = getVideoJobRef.operationName;
console.log(name);
```

### Variables
The `GetVideoJob` query requires an argument of type `GetVideoJobVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface GetVideoJobVariables {
  id: UUIDString;
}
```
### Return Type
Recall that executing the `GetVideoJob` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `GetVideoJobData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
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
```
### Using `GetVideoJob`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, getVideoJob, GetVideoJobVariables } from '@dataconnect/generated';

// The `GetVideoJob` query requires an argument of type `GetVideoJobVariables`:
const getVideoJobVars: GetVideoJobVariables = {
  id: ..., 
};

// Call the `getVideoJob()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await getVideoJob(getVideoJobVars);
// Variables can be defined inline as well.
const { data } = await getVideoJob({ id: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await getVideoJob(dataConnect, getVideoJobVars);

console.log(data.videoJob);

// Or, you can use the `Promise` API.
getVideoJob(getVideoJobVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob);
});
```

### Using `GetVideoJob`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, getVideoJobRef, GetVideoJobVariables } from '@dataconnect/generated';

// The `GetVideoJob` query requires an argument of type `GetVideoJobVariables`:
const getVideoJobVars: GetVideoJobVariables = {
  id: ..., 
};

// Call the `getVideoJobRef()` function to get a reference to the query.
const ref = getVideoJobRef(getVideoJobVars);
// Variables can be defined inline as well.
const ref = getVideoJobRef({ id: ..., });

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = getVideoJobRef(dataConnect, getVideoJobVars);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.videoJob);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJob);
});
```

## ListJobEvents
You can execute the `ListJobEvents` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listJobEvents(vars: ListJobEventsVariables): QueryPromise<ListJobEventsData, ListJobEventsVariables>;

interface ListJobEventsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: ListJobEventsVariables): QueryRef<ListJobEventsData, ListJobEventsVariables>;
}
export const listJobEventsRef: ListJobEventsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listJobEvents(dc: DataConnect, vars: ListJobEventsVariables): QueryPromise<ListJobEventsData, ListJobEventsVariables>;

interface ListJobEventsRef {
  ...
  (dc: DataConnect, vars: ListJobEventsVariables): QueryRef<ListJobEventsData, ListJobEventsVariables>;
}
export const listJobEventsRef: ListJobEventsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listJobEventsRef:
```typescript
const name = listJobEventsRef.operationName;
console.log(name);
```

### Variables
The `ListJobEvents` query requires an argument of type `ListJobEventsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface ListJobEventsVariables {
  jobId: UUIDString;
}
```
### Return Type
Recall that executing the `ListJobEvents` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListJobEventsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface ListJobEventsData {
  jobEvents: ({
    id: UUIDString;
    eventType: string;
    agent?: string | null;
    details?: string | null;
    timestamp: TimestampString;
  } & JobEvent_Key)[];
}
```
### Using `ListJobEvents`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listJobEvents, ListJobEventsVariables } from '@dataconnect/generated';

// The `ListJobEvents` query requires an argument of type `ListJobEventsVariables`:
const listJobEventsVars: ListJobEventsVariables = {
  jobId: ..., 
};

// Call the `listJobEvents()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listJobEvents(listJobEventsVars);
// Variables can be defined inline as well.
const { data } = await listJobEvents({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listJobEvents(dataConnect, listJobEventsVars);

console.log(data.jobEvents);

// Or, you can use the `Promise` API.
listJobEvents(listJobEventsVars).then((response) => {
  const data = response.data;
  console.log(data.jobEvents);
});
```

### Using `ListJobEvents`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listJobEventsRef, ListJobEventsVariables } from '@dataconnect/generated';

// The `ListJobEvents` query requires an argument of type `ListJobEventsVariables`:
const listJobEventsVars: ListJobEventsVariables = {
  jobId: ..., 
};

// Call the `listJobEventsRef()` function to get a reference to the query.
const ref = listJobEventsRef(listJobEventsVars);
// Variables can be defined inline as well.
const ref = listJobEventsRef({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listJobEventsRef(dataConnect, listJobEventsVars);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.jobEvents);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.jobEvents);
});
```

## ListVideoEmbeddings
You can execute the `ListVideoEmbeddings` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listVideoEmbeddings(vars?: ListVideoEmbeddingsVariables): QueryPromise<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;

interface ListVideoEmbeddingsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars?: ListVideoEmbeddingsVariables): QueryRef<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;
}
export const listVideoEmbeddingsRef: ListVideoEmbeddingsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listVideoEmbeddings(dc: DataConnect, vars?: ListVideoEmbeddingsVariables): QueryPromise<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;

interface ListVideoEmbeddingsRef {
  ...
  (dc: DataConnect, vars?: ListVideoEmbeddingsVariables): QueryRef<ListVideoEmbeddingsData, ListVideoEmbeddingsVariables>;
}
export const listVideoEmbeddingsRef: ListVideoEmbeddingsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listVideoEmbeddingsRef:
```typescript
const name = listVideoEmbeddingsRef.operationName;
console.log(name);
```

### Variables
The `ListVideoEmbeddings` query has an optional argument of type `ListVideoEmbeddingsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface ListVideoEmbeddingsVariables {
  limit?: number | null;
}
```
### Return Type
Recall that executing the `ListVideoEmbeddings` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListVideoEmbeddingsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
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
```
### Using `ListVideoEmbeddings`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listVideoEmbeddings, ListVideoEmbeddingsVariables } from '@dataconnect/generated';

// The `ListVideoEmbeddings` query has an optional argument of type `ListVideoEmbeddingsVariables`:
const listVideoEmbeddingsVars: ListVideoEmbeddingsVariables = {
  limit: ..., // optional
};

// Call the `listVideoEmbeddings()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listVideoEmbeddings(listVideoEmbeddingsVars);
// Variables can be defined inline as well.
const { data } = await listVideoEmbeddings({ limit: ..., });
// Since all variables are optional for this query, you can omit the `ListVideoEmbeddingsVariables` argument.
const { data } = await listVideoEmbeddings();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listVideoEmbeddings(dataConnect, listVideoEmbeddingsVars);

console.log(data.videoEmbeddings);

// Or, you can use the `Promise` API.
listVideoEmbeddings(listVideoEmbeddingsVars).then((response) => {
  const data = response.data;
  console.log(data.videoEmbeddings);
});
```

### Using `ListVideoEmbeddings`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listVideoEmbeddingsRef, ListVideoEmbeddingsVariables } from '@dataconnect/generated';

// The `ListVideoEmbeddings` query has an optional argument of type `ListVideoEmbeddingsVariables`:
const listVideoEmbeddingsVars: ListVideoEmbeddingsVariables = {
  limit: ..., // optional
};

// Call the `listVideoEmbeddingsRef()` function to get a reference to the query.
const ref = listVideoEmbeddingsRef(listVideoEmbeddingsVars);
// Variables can be defined inline as well.
const ref = listVideoEmbeddingsRef({ limit: ..., });
// Since all variables are optional for this query, you can omit the `ListVideoEmbeddingsVariables` argument.
const ref = listVideoEmbeddingsRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listVideoEmbeddingsRef(dataConnect, listVideoEmbeddingsVars);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.videoEmbeddings);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.videoEmbeddings);
});
```

## ListFailedJobs
You can execute the `ListFailedJobs` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listFailedJobs(): QueryPromise<ListFailedJobsData, undefined>;

interface ListFailedJobsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<ListFailedJobsData, undefined>;
}
export const listFailedJobsRef: ListFailedJobsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listFailedJobs(dc: DataConnect): QueryPromise<ListFailedJobsData, undefined>;

interface ListFailedJobsRef {
  ...
  (dc: DataConnect): QueryRef<ListFailedJobsData, undefined>;
}
export const listFailedJobsRef: ListFailedJobsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listFailedJobsRef:
```typescript
const name = listFailedJobsRef.operationName;
console.log(name);
```

### Variables
The `ListFailedJobs` query has no variables.
### Return Type
Recall that executing the `ListFailedJobs` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListFailedJobsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface ListFailedJobsData {
  videoJobs: ({
    id: UUIDString;
    videoUrl: string;
    error?: string | null;
    executedAgents: string[];
    updatedAt: TimestampString;
  } & VideoJob_Key)[];
}
```
### Using `ListFailedJobs`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listFailedJobs } from '@dataconnect/generated';


// Call the `listFailedJobs()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listFailedJobs();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listFailedJobs(dataConnect);

console.log(data.videoJobs);

// Or, you can use the `Promise` API.
listFailedJobs().then((response) => {
  const data = response.data;
  console.log(data.videoJobs);
});
```

### Using `ListFailedJobs`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listFailedJobsRef } from '@dataconnect/generated';


// Call the `listFailedJobsRef()` function to get a reference to the query.
const ref = listFailedJobsRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listFailedJobsRef(dataConnect);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.videoJobs);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJobs);
});
```

# Mutations

There are two ways to execute a Data Connect Mutation using the generated Web SDK:
- Using a Mutation Reference function, which returns a `MutationRef`
  - The `MutationRef` can be used as an argument to `executeMutation()`, which will execute the Mutation and return a `MutationPromise`
- Using an action shortcut function, which returns a `MutationPromise`
  - Calling the action shortcut function will execute the Mutation and return a `MutationPromise`

The following is true for both the action shortcut function and the `MutationRef` function:
- The `MutationPromise` returned will resolve to the result of the Mutation once it has finished executing
- If the Mutation accepts arguments, both the action shortcut function and the `MutationRef` function accept a single argument: an object that contains all the required variables (and the optional variables) for the Mutation
- Both functions can be called with or without passing in a `DataConnect` instance as an argument. If no `DataConnect` argument is passed in, then the generated SDK will call `getDataConnect(connectorConfig)` behind the scenes for you.

Below are examples of how to use the `example` connector's generated functions to execute each mutation. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-mutations).

## CreateExampleJob
You can execute the `CreateExampleJob` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
createExampleJob(vars: CreateExampleJobVariables): MutationPromise<CreateExampleJobData, CreateExampleJobVariables>;

interface CreateExampleJobRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateExampleJobVariables): MutationRef<CreateExampleJobData, CreateExampleJobVariables>;
}
export const createExampleJobRef: CreateExampleJobRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
createExampleJob(dc: DataConnect, vars: CreateExampleJobVariables): MutationPromise<CreateExampleJobData, CreateExampleJobVariables>;

interface CreateExampleJobRef {
  ...
  (dc: DataConnect, vars: CreateExampleJobVariables): MutationRef<CreateExampleJobData, CreateExampleJobVariables>;
}
export const createExampleJobRef: CreateExampleJobRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the createExampleJobRef:
```typescript
const name = createExampleJobRef.operationName;
console.log(name);
```

### Variables
The `CreateExampleJob` mutation requires an argument of type `CreateExampleJobVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface CreateExampleJobVariables {
  videoUrl: string;
  source: string;
  taskType: string;
}
```
### Return Type
Recall that executing the `CreateExampleJob` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `CreateExampleJobData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface CreateExampleJobData {
  videoJob_insert: VideoJob_Key;
}
```
### Using `CreateExampleJob`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, createExampleJob, CreateExampleJobVariables } from '@dataconnect/generated';

// The `CreateExampleJob` mutation requires an argument of type `CreateExampleJobVariables`:
const createExampleJobVars: CreateExampleJobVariables = {
  videoUrl: ..., 
  source: ..., 
  taskType: ..., 
};

// Call the `createExampleJob()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await createExampleJob(createExampleJobVars);
// Variables can be defined inline as well.
const { data } = await createExampleJob({ videoUrl: ..., source: ..., taskType: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await createExampleJob(dataConnect, createExampleJobVars);

console.log(data.videoJob_insert);

// Or, you can use the `Promise` API.
createExampleJob(createExampleJobVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob_insert);
});
```

### Using `CreateExampleJob`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, createExampleJobRef, CreateExampleJobVariables } from '@dataconnect/generated';

// The `CreateExampleJob` mutation requires an argument of type `CreateExampleJobVariables`:
const createExampleJobVars: CreateExampleJobVariables = {
  videoUrl: ..., 
  source: ..., 
  taskType: ..., 
};

// Call the `createExampleJobRef()` function to get a reference to the mutation.
const ref = createExampleJobRef(createExampleJobVars);
// Variables can be defined inline as well.
const ref = createExampleJobRef({ videoUrl: ..., source: ..., taskType: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = createExampleJobRef(dataConnect, createExampleJobVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.videoJob_insert);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJob_insert);
});
```

## RecordExampleEvent
You can execute the `RecordExampleEvent` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
recordExampleEvent(vars: RecordExampleEventVariables): MutationPromise<RecordExampleEventData, RecordExampleEventVariables>;

interface RecordExampleEventRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: RecordExampleEventVariables): MutationRef<RecordExampleEventData, RecordExampleEventVariables>;
}
export const recordExampleEventRef: RecordExampleEventRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
recordExampleEvent(dc: DataConnect, vars: RecordExampleEventVariables): MutationPromise<RecordExampleEventData, RecordExampleEventVariables>;

interface RecordExampleEventRef {
  ...
  (dc: DataConnect, vars: RecordExampleEventVariables): MutationRef<RecordExampleEventData, RecordExampleEventVariables>;
}
export const recordExampleEventRef: RecordExampleEventRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the recordExampleEventRef:
```typescript
const name = recordExampleEventRef.operationName;
console.log(name);
```

### Variables
The `RecordExampleEvent` mutation requires an argument of type `RecordExampleEventVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface RecordExampleEventVariables {
  jobId: UUIDString;
  eventType: string;
  agent?: string | null;
  details?: string | null;
}
```
### Return Type
Recall that executing the `RecordExampleEvent` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `RecordExampleEventData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface RecordExampleEventData {
  jobEvent_insert: JobEvent_Key;
}
```
### Using `RecordExampleEvent`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, recordExampleEvent, RecordExampleEventVariables } from '@dataconnect/generated';

// The `RecordExampleEvent` mutation requires an argument of type `RecordExampleEventVariables`:
const recordExampleEventVars: RecordExampleEventVariables = {
  jobId: ..., 
  eventType: ..., 
  agent: ..., // optional
  details: ..., // optional
};

// Call the `recordExampleEvent()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await recordExampleEvent(recordExampleEventVars);
// Variables can be defined inline as well.
const { data } = await recordExampleEvent({ jobId: ..., eventType: ..., agent: ..., details: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await recordExampleEvent(dataConnect, recordExampleEventVars);

console.log(data.jobEvent_insert);

// Or, you can use the `Promise` API.
recordExampleEvent(recordExampleEventVars).then((response) => {
  const data = response.data;
  console.log(data.jobEvent_insert);
});
```

### Using `RecordExampleEvent`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, recordExampleEventRef, RecordExampleEventVariables } from '@dataconnect/generated';

// The `RecordExampleEvent` mutation requires an argument of type `RecordExampleEventVariables`:
const recordExampleEventVars: RecordExampleEventVariables = {
  jobId: ..., 
  eventType: ..., 
  agent: ..., // optional
  details: ..., // optional
};

// Call the `recordExampleEventRef()` function to get a reference to the mutation.
const ref = recordExampleEventRef(recordExampleEventVars);
// Variables can be defined inline as well.
const ref = recordExampleEventRef({ jobId: ..., eventType: ..., agent: ..., details: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = recordExampleEventRef(dataConnect, recordExampleEventVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.jobEvent_insert);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.jobEvent_insert);
});
```

## DeleteExampleEvent
You can execute the `DeleteExampleEvent` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
deleteExampleEvent(vars: DeleteExampleEventVariables): MutationPromise<DeleteExampleEventData, DeleteExampleEventVariables>;

interface DeleteExampleEventRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: DeleteExampleEventVariables): MutationRef<DeleteExampleEventData, DeleteExampleEventVariables>;
}
export const deleteExampleEventRef: DeleteExampleEventRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
deleteExampleEvent(dc: DataConnect, vars: DeleteExampleEventVariables): MutationPromise<DeleteExampleEventData, DeleteExampleEventVariables>;

interface DeleteExampleEventRef {
  ...
  (dc: DataConnect, vars: DeleteExampleEventVariables): MutationRef<DeleteExampleEventData, DeleteExampleEventVariables>;
}
export const deleteExampleEventRef: DeleteExampleEventRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the deleteExampleEventRef:
```typescript
const name = deleteExampleEventRef.operationName;
console.log(name);
```

### Variables
The `DeleteExampleEvent` mutation requires an argument of type `DeleteExampleEventVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface DeleteExampleEventVariables {
  id: UUIDString;
}
```
### Return Type
Recall that executing the `DeleteExampleEvent` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `DeleteExampleEventData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface DeleteExampleEventData {
  jobEvent_delete?: JobEvent_Key | null;
}
```
### Using `DeleteExampleEvent`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, deleteExampleEvent, DeleteExampleEventVariables } from '@dataconnect/generated';

// The `DeleteExampleEvent` mutation requires an argument of type `DeleteExampleEventVariables`:
const deleteExampleEventVars: DeleteExampleEventVariables = {
  id: ..., 
};

// Call the `deleteExampleEvent()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await deleteExampleEvent(deleteExampleEventVars);
// Variables can be defined inline as well.
const { data } = await deleteExampleEvent({ id: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await deleteExampleEvent(dataConnect, deleteExampleEventVars);

console.log(data.jobEvent_delete);

// Or, you can use the `Promise` API.
deleteExampleEvent(deleteExampleEventVars).then((response) => {
  const data = response.data;
  console.log(data.jobEvent_delete);
});
```

### Using `DeleteExampleEvent`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, deleteExampleEventRef, DeleteExampleEventVariables } from '@dataconnect/generated';

// The `DeleteExampleEvent` mutation requires an argument of type `DeleteExampleEventVariables`:
const deleteExampleEventVars: DeleteExampleEventVariables = {
  id: ..., 
};

// Call the `deleteExampleEventRef()` function to get a reference to the mutation.
const ref = deleteExampleEventRef(deleteExampleEventVars);
// Variables can be defined inline as well.
const ref = deleteExampleEventRef({ id: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = deleteExampleEventRef(dataConnect, deleteExampleEventVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.jobEvent_delete);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.jobEvent_delete);
});
```

