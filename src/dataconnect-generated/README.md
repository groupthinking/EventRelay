# Generated TypeScript README
This README will guide you through the process of using the generated JavaScript SDK package for the connector `jobs`. It will also provide examples on how to use your generated SDK to call your Data Connect queries and mutations.

***NOTE:** This README is generated alongside the generated SDK. If you make changes to this file, they will be overwritten when the SDK is regenerated.*

# Table of Contents
- [**Overview**](#generated-javascript-readme)
- [**Accessing the connector**](#accessing-the-connector)
  - [*Connecting to the local Emulator*](#connecting-to-the-local-emulator)
- [**Queries**](#queries)
  - [*getJob*](#getjob)
  - [*listJobs*](#listjobs)
  - [*getJobEvents*](#getjobevents)
  - [*listEmbeddings*](#listembeddings)
  - [*getJobEmbeddings*](#getjobembeddings)
- [**Mutations**](#mutations)
  - [*createVideoJob*](#createvideojob)
  - [*updateJobStatus*](#updatejobstatus)
  - [*completeJob*](#completejob)
  - [*failJob*](#failjob)
  - [*recordJobEvent*](#recordjobevent)
  - [*deleteJobEmbeddings*](#deletejobembeddings)

# Accessing the connector
A connector is a collection of Queries and Mutations. One SDK is generated for each connector - this SDK is generated for the connector `jobs`. You can find more information about connectors in the [Data Connect documentation](https://firebase.google.com/docs/data-connect#how-does).

You can use this generated SDK by importing from the package `@video-analyzer/dataconnect` as shown below. Both CommonJS and ESM imports are supported.

You can also follow the instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#set-client).

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@video-analyzer/dataconnect';

const dataConnect = getDataConnect(connectorConfig);
```

## Connecting to the local Emulator
By default, the connector will connect to the production service.

To connect to the emulator, you can use the following code.
You can also follow the emulator instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#instrument-clients).

```typescript
import { connectDataConnectEmulator, getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@video-analyzer/dataconnect';

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

Below are examples of how to use the `jobs` connector's generated functions to execute each query. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-queries).

## getJob
You can execute the `getJob` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
getJob(vars: GetJobVariables): QueryPromise<GetJobData, GetJobVariables>;

interface GetJobRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetJobVariables): QueryRef<GetJobData, GetJobVariables>;
}
export const getJobRef: GetJobRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
getJob(dc: DataConnect, vars: GetJobVariables): QueryPromise<GetJobData, GetJobVariables>;

interface GetJobRef {
  ...
  (dc: DataConnect, vars: GetJobVariables): QueryRef<GetJobData, GetJobVariables>;
}
export const getJobRef: GetJobRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the getJobRef:
```typescript
const name = getJobRef.operationName;
console.log(name);
```

### Variables
The `getJob` query requires an argument of type `GetJobVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface GetJobVariables {
  id: UUIDString;
}
```
### Return Type
Recall that executing the `getJob` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `GetJobData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface GetJobData {
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
    createdAt: TimestampString;
    updatedAt: TimestampString;
  } & VideoJob_Key;
}
```
### Using `getJob`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, getJob, GetJobVariables } from '@video-analyzer/dataconnect';

// The `getJob` query requires an argument of type `GetJobVariables`:
const getJobVars: GetJobVariables = {
  id: ..., 
};

// Call the `getJob()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await getJob(getJobVars);
// Variables can be defined inline as well.
const { data } = await getJob({ id: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await getJob(dataConnect, getJobVars);

console.log(data.videoJob);

// Or, you can use the `Promise` API.
getJob(getJobVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob);
});
```

### Using `getJob`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, getJobRef, GetJobVariables } from '@video-analyzer/dataconnect';

// The `getJob` query requires an argument of type `GetJobVariables`:
const getJobVars: GetJobVariables = {
  id: ..., 
};

// Call the `getJobRef()` function to get a reference to the query.
const ref = getJobRef(getJobVars);
// Variables can be defined inline as well.
const ref = getJobRef({ id: ..., });

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = getJobRef(dataConnect, getJobVars);

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

## listJobs
You can execute the `listJobs` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listJobs(vars?: ListJobsVariables): QueryPromise<ListJobsData, ListJobsVariables>;

interface ListJobsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars?: ListJobsVariables): QueryRef<ListJobsData, ListJobsVariables>;
}
export const listJobsRef: ListJobsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listJobs(dc: DataConnect, vars?: ListJobsVariables): QueryPromise<ListJobsData, ListJobsVariables>;

interface ListJobsRef {
  ...
  (dc: DataConnect, vars?: ListJobsVariables): QueryRef<ListJobsData, ListJobsVariables>;
}
export const listJobsRef: ListJobsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listJobsRef:
```typescript
const name = listJobsRef.operationName;
console.log(name);
```

### Variables
The `listJobs` query has an optional argument of type `ListJobsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface ListJobsVariables {
  limit?: number | null;
}
```
### Return Type
Recall that executing the `listJobs` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListJobsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
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
```
### Using `listJobs`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listJobs, ListJobsVariables } from '@video-analyzer/dataconnect';

// The `listJobs` query has an optional argument of type `ListJobsVariables`:
const listJobsVars: ListJobsVariables = {
  limit: ..., // optional
};

// Call the `listJobs()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listJobs(listJobsVars);
// Variables can be defined inline as well.
const { data } = await listJobs({ limit: ..., });
// Since all variables are optional for this query, you can omit the `ListJobsVariables` argument.
const { data } = await listJobs();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listJobs(dataConnect, listJobsVars);

console.log(data.videoJobs);

// Or, you can use the `Promise` API.
listJobs(listJobsVars).then((response) => {
  const data = response.data;
  console.log(data.videoJobs);
});
```

### Using `listJobs`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listJobsRef, ListJobsVariables } from '@video-analyzer/dataconnect';

// The `listJobs` query has an optional argument of type `ListJobsVariables`:
const listJobsVars: ListJobsVariables = {
  limit: ..., // optional
};

// Call the `listJobsRef()` function to get a reference to the query.
const ref = listJobsRef(listJobsVars);
// Variables can be defined inline as well.
const ref = listJobsRef({ limit: ..., });
// Since all variables are optional for this query, you can omit the `ListJobsVariables` argument.
const ref = listJobsRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listJobsRef(dataConnect, listJobsVars);

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

## getJobEvents
You can execute the `getJobEvents` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
getJobEvents(vars: GetJobEventsVariables): QueryPromise<GetJobEventsData, GetJobEventsVariables>;

interface GetJobEventsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetJobEventsVariables): QueryRef<GetJobEventsData, GetJobEventsVariables>;
}
export const getJobEventsRef: GetJobEventsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
getJobEvents(dc: DataConnect, vars: GetJobEventsVariables): QueryPromise<GetJobEventsData, GetJobEventsVariables>;

interface GetJobEventsRef {
  ...
  (dc: DataConnect, vars: GetJobEventsVariables): QueryRef<GetJobEventsData, GetJobEventsVariables>;
}
export const getJobEventsRef: GetJobEventsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the getJobEventsRef:
```typescript
const name = getJobEventsRef.operationName;
console.log(name);
```

### Variables
The `getJobEvents` query requires an argument of type `GetJobEventsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface GetJobEventsVariables {
  jobId: UUIDString;
}
```
### Return Type
Recall that executing the `getJobEvents` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `GetJobEventsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface GetJobEventsData {
  jobEvents: ({
    id: UUIDString;
    eventType: string;
    agent?: string | null;
    details?: string | null;
    timestamp: TimestampString;
  } & JobEvent_Key)[];
}
```
### Using `getJobEvents`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, getJobEvents, GetJobEventsVariables } from '@video-analyzer/dataconnect';

// The `getJobEvents` query requires an argument of type `GetJobEventsVariables`:
const getJobEventsVars: GetJobEventsVariables = {
  jobId: ..., 
};

// Call the `getJobEvents()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await getJobEvents(getJobEventsVars);
// Variables can be defined inline as well.
const { data } = await getJobEvents({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await getJobEvents(dataConnect, getJobEventsVars);

console.log(data.jobEvents);

// Or, you can use the `Promise` API.
getJobEvents(getJobEventsVars).then((response) => {
  const data = response.data;
  console.log(data.jobEvents);
});
```

### Using `getJobEvents`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, getJobEventsRef, GetJobEventsVariables } from '@video-analyzer/dataconnect';

// The `getJobEvents` query requires an argument of type `GetJobEventsVariables`:
const getJobEventsVars: GetJobEventsVariables = {
  jobId: ..., 
};

// Call the `getJobEventsRef()` function to get a reference to the query.
const ref = getJobEventsRef(getJobEventsVars);
// Variables can be defined inline as well.
const ref = getJobEventsRef({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = getJobEventsRef(dataConnect, getJobEventsVars);

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

## listEmbeddings
You can execute the `listEmbeddings` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listEmbeddings(vars?: ListEmbeddingsVariables): QueryPromise<ListEmbeddingsData, ListEmbeddingsVariables>;

interface ListEmbeddingsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars?: ListEmbeddingsVariables): QueryRef<ListEmbeddingsData, ListEmbeddingsVariables>;
}
export const listEmbeddingsRef: ListEmbeddingsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listEmbeddings(dc: DataConnect, vars?: ListEmbeddingsVariables): QueryPromise<ListEmbeddingsData, ListEmbeddingsVariables>;

interface ListEmbeddingsRef {
  ...
  (dc: DataConnect, vars?: ListEmbeddingsVariables): QueryRef<ListEmbeddingsData, ListEmbeddingsVariables>;
}
export const listEmbeddingsRef: ListEmbeddingsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listEmbeddingsRef:
```typescript
const name = listEmbeddingsRef.operationName;
console.log(name);
```

### Variables
The `listEmbeddings` query has an optional argument of type `ListEmbeddingsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface ListEmbeddingsVariables {
  limit?: number | null;
}
```
### Return Type
Recall that executing the `listEmbeddings` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListEmbeddingsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
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
```
### Using `listEmbeddings`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listEmbeddings, ListEmbeddingsVariables } from '@video-analyzer/dataconnect';

// The `listEmbeddings` query has an optional argument of type `ListEmbeddingsVariables`:
const listEmbeddingsVars: ListEmbeddingsVariables = {
  limit: ..., // optional
};

// Call the `listEmbeddings()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listEmbeddings(listEmbeddingsVars);
// Variables can be defined inline as well.
const { data } = await listEmbeddings({ limit: ..., });
// Since all variables are optional for this query, you can omit the `ListEmbeddingsVariables` argument.
const { data } = await listEmbeddings();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listEmbeddings(dataConnect, listEmbeddingsVars);

console.log(data.videoEmbeddings);

// Or, you can use the `Promise` API.
listEmbeddings(listEmbeddingsVars).then((response) => {
  const data = response.data;
  console.log(data.videoEmbeddings);
});
```

### Using `listEmbeddings`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listEmbeddingsRef, ListEmbeddingsVariables } from '@video-analyzer/dataconnect';

// The `listEmbeddings` query has an optional argument of type `ListEmbeddingsVariables`:
const listEmbeddingsVars: ListEmbeddingsVariables = {
  limit: ..., // optional
};

// Call the `listEmbeddingsRef()` function to get a reference to the query.
const ref = listEmbeddingsRef(listEmbeddingsVars);
// Variables can be defined inline as well.
const ref = listEmbeddingsRef({ limit: ..., });
// Since all variables are optional for this query, you can omit the `ListEmbeddingsVariables` argument.
const ref = listEmbeddingsRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listEmbeddingsRef(dataConnect, listEmbeddingsVars);

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

## getJobEmbeddings
You can execute the `getJobEmbeddings` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
getJobEmbeddings(vars: GetJobEmbeddingsVariables): QueryPromise<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;

interface GetJobEmbeddingsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: GetJobEmbeddingsVariables): QueryRef<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;
}
export const getJobEmbeddingsRef: GetJobEmbeddingsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
getJobEmbeddings(dc: DataConnect, vars: GetJobEmbeddingsVariables): QueryPromise<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;

interface GetJobEmbeddingsRef {
  ...
  (dc: DataConnect, vars: GetJobEmbeddingsVariables): QueryRef<GetJobEmbeddingsData, GetJobEmbeddingsVariables>;
}
export const getJobEmbeddingsRef: GetJobEmbeddingsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the getJobEmbeddingsRef:
```typescript
const name = getJobEmbeddingsRef.operationName;
console.log(name);
```

### Variables
The `getJobEmbeddings` query requires an argument of type `GetJobEmbeddingsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface GetJobEmbeddingsVariables {
  jobId: UUIDString;
}
```
### Return Type
Recall that executing the `getJobEmbeddings` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `GetJobEmbeddingsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface GetJobEmbeddingsData {
  videoEmbeddings: ({
    id: UUIDString;
    segmentType: string;
    segmentIndex: number;
    content: string;
    createdAt: TimestampString;
  } & VideoEmbedding_Key)[];
}
```
### Using `getJobEmbeddings`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, getJobEmbeddings, GetJobEmbeddingsVariables } from '@video-analyzer/dataconnect';

// The `getJobEmbeddings` query requires an argument of type `GetJobEmbeddingsVariables`:
const getJobEmbeddingsVars: GetJobEmbeddingsVariables = {
  jobId: ..., 
};

// Call the `getJobEmbeddings()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await getJobEmbeddings(getJobEmbeddingsVars);
// Variables can be defined inline as well.
const { data } = await getJobEmbeddings({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await getJobEmbeddings(dataConnect, getJobEmbeddingsVars);

console.log(data.videoEmbeddings);

// Or, you can use the `Promise` API.
getJobEmbeddings(getJobEmbeddingsVars).then((response) => {
  const data = response.data;
  console.log(data.videoEmbeddings);
});
```

### Using `getJobEmbeddings`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, getJobEmbeddingsRef, GetJobEmbeddingsVariables } from '@video-analyzer/dataconnect';

// The `getJobEmbeddings` query requires an argument of type `GetJobEmbeddingsVariables`:
const getJobEmbeddingsVars: GetJobEmbeddingsVariables = {
  jobId: ..., 
};

// Call the `getJobEmbeddingsRef()` function to get a reference to the query.
const ref = getJobEmbeddingsRef(getJobEmbeddingsVars);
// Variables can be defined inline as well.
const ref = getJobEmbeddingsRef({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = getJobEmbeddingsRef(dataConnect, getJobEmbeddingsVars);

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

Below are examples of how to use the `jobs` connector's generated functions to execute each mutation. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-mutations).

## createVideoJob
You can execute the `createVideoJob` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
createVideoJob(vars: CreateVideoJobVariables): MutationPromise<CreateVideoJobData, CreateVideoJobVariables>;

interface CreateVideoJobRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateVideoJobVariables): MutationRef<CreateVideoJobData, CreateVideoJobVariables>;
}
export const createVideoJobRef: CreateVideoJobRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
createVideoJob(dc: DataConnect, vars: CreateVideoJobVariables): MutationPromise<CreateVideoJobData, CreateVideoJobVariables>;

interface CreateVideoJobRef {
  ...
  (dc: DataConnect, vars: CreateVideoJobVariables): MutationRef<CreateVideoJobData, CreateVideoJobVariables>;
}
export const createVideoJobRef: CreateVideoJobRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the createVideoJobRef:
```typescript
const name = createVideoJobRef.operationName;
console.log(name);
```

### Variables
The `createVideoJob` mutation requires an argument of type `CreateVideoJobVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface CreateVideoJobVariables {
  videoUrl: string;
  source: string;
  taskType: string;
}
```
### Return Type
Recall that executing the `createVideoJob` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `CreateVideoJobData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface CreateVideoJobData {
  videoJob_insert: VideoJob_Key;
}
```
### Using `createVideoJob`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, createVideoJob, CreateVideoJobVariables } from '@video-analyzer/dataconnect';

// The `createVideoJob` mutation requires an argument of type `CreateVideoJobVariables`:
const createVideoJobVars: CreateVideoJobVariables = {
  videoUrl: ..., 
  source: ..., 
  taskType: ..., 
};

// Call the `createVideoJob()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await createVideoJob(createVideoJobVars);
// Variables can be defined inline as well.
const { data } = await createVideoJob({ videoUrl: ..., source: ..., taskType: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await createVideoJob(dataConnect, createVideoJobVars);

console.log(data.videoJob_insert);

// Or, you can use the `Promise` API.
createVideoJob(createVideoJobVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob_insert);
});
```

### Using `createVideoJob`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, createVideoJobRef, CreateVideoJobVariables } from '@video-analyzer/dataconnect';

// The `createVideoJob` mutation requires an argument of type `CreateVideoJobVariables`:
const createVideoJobVars: CreateVideoJobVariables = {
  videoUrl: ..., 
  source: ..., 
  taskType: ..., 
};

// Call the `createVideoJobRef()` function to get a reference to the mutation.
const ref = createVideoJobRef(createVideoJobVars);
// Variables can be defined inline as well.
const ref = createVideoJobRef({ videoUrl: ..., source: ..., taskType: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = createVideoJobRef(dataConnect, createVideoJobVars);

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

## updateJobStatus
You can execute the `updateJobStatus` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
updateJobStatus(vars: UpdateJobStatusVariables): MutationPromise<UpdateJobStatusData, UpdateJobStatusVariables>;

interface UpdateJobStatusRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: UpdateJobStatusVariables): MutationRef<UpdateJobStatusData, UpdateJobStatusVariables>;
}
export const updateJobStatusRef: UpdateJobStatusRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
updateJobStatus(dc: DataConnect, vars: UpdateJobStatusVariables): MutationPromise<UpdateJobStatusData, UpdateJobStatusVariables>;

interface UpdateJobStatusRef {
  ...
  (dc: DataConnect, vars: UpdateJobStatusVariables): MutationRef<UpdateJobStatusData, UpdateJobStatusVariables>;
}
export const updateJobStatusRef: UpdateJobStatusRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the updateJobStatusRef:
```typescript
const name = updateJobStatusRef.operationName;
console.log(name);
```

### Variables
The `updateJobStatus` mutation requires an argument of type `UpdateJobStatusVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface UpdateJobStatusVariables {
  id: UUIDString;
  status: string;
  executedAgents?: string[] | null;
}
```
### Return Type
Recall that executing the `updateJobStatus` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `UpdateJobStatusData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface UpdateJobStatusData {
  videoJob_update?: VideoJob_Key | null;
}
```
### Using `updateJobStatus`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, updateJobStatus, UpdateJobStatusVariables } from '@video-analyzer/dataconnect';

// The `updateJobStatus` mutation requires an argument of type `UpdateJobStatusVariables`:
const updateJobStatusVars: UpdateJobStatusVariables = {
  id: ..., 
  status: ..., 
  executedAgents: ..., // optional
};

// Call the `updateJobStatus()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await updateJobStatus(updateJobStatusVars);
// Variables can be defined inline as well.
const { data } = await updateJobStatus({ id: ..., status: ..., executedAgents: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await updateJobStatus(dataConnect, updateJobStatusVars);

console.log(data.videoJob_update);

// Or, you can use the `Promise` API.
updateJobStatus(updateJobStatusVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob_update);
});
```

### Using `updateJobStatus`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, updateJobStatusRef, UpdateJobStatusVariables } from '@video-analyzer/dataconnect';

// The `updateJobStatus` mutation requires an argument of type `UpdateJobStatusVariables`:
const updateJobStatusVars: UpdateJobStatusVariables = {
  id: ..., 
  status: ..., 
  executedAgents: ..., // optional
};

// Call the `updateJobStatusRef()` function to get a reference to the mutation.
const ref = updateJobStatusRef(updateJobStatusVars);
// Variables can be defined inline as well.
const ref = updateJobStatusRef({ id: ..., status: ..., executedAgents: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = updateJobStatusRef(dataConnect, updateJobStatusVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.videoJob_update);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJob_update);
});
```

## completeJob
You can execute the `completeJob` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
completeJob(vars: CompleteJobVariables): MutationPromise<CompleteJobData, CompleteJobVariables>;

interface CompleteJobRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: CompleteJobVariables): MutationRef<CompleteJobData, CompleteJobVariables>;
}
export const completeJobRef: CompleteJobRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
completeJob(dc: DataConnect, vars: CompleteJobVariables): MutationPromise<CompleteJobData, CompleteJobVariables>;

interface CompleteJobRef {
  ...
  (dc: DataConnect, vars: CompleteJobVariables): MutationRef<CompleteJobData, CompleteJobVariables>;
}
export const completeJobRef: CompleteJobRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the completeJobRef:
```typescript
const name = completeJobRef.operationName;
console.log(name);
```

### Variables
The `completeJob` mutation requires an argument of type `CompleteJobVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface CompleteJobVariables {
  id: UUIDString;
  resultJson: string;
  title?: string | null;
}
```
### Return Type
Recall that executing the `completeJob` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `CompleteJobData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface CompleteJobData {
  videoJob_update?: VideoJob_Key | null;
}
```
### Using `completeJob`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, completeJob, CompleteJobVariables } from '@video-analyzer/dataconnect';

// The `completeJob` mutation requires an argument of type `CompleteJobVariables`:
const completeJobVars: CompleteJobVariables = {
  id: ..., 
  resultJson: ..., 
  title: ..., // optional
};

// Call the `completeJob()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await completeJob(completeJobVars);
// Variables can be defined inline as well.
const { data } = await completeJob({ id: ..., resultJson: ..., title: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await completeJob(dataConnect, completeJobVars);

console.log(data.videoJob_update);

// Or, you can use the `Promise` API.
completeJob(completeJobVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob_update);
});
```

### Using `completeJob`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, completeJobRef, CompleteJobVariables } from '@video-analyzer/dataconnect';

// The `completeJob` mutation requires an argument of type `CompleteJobVariables`:
const completeJobVars: CompleteJobVariables = {
  id: ..., 
  resultJson: ..., 
  title: ..., // optional
};

// Call the `completeJobRef()` function to get a reference to the mutation.
const ref = completeJobRef(completeJobVars);
// Variables can be defined inline as well.
const ref = completeJobRef({ id: ..., resultJson: ..., title: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = completeJobRef(dataConnect, completeJobVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.videoJob_update);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJob_update);
});
```

## failJob
You can execute the `failJob` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
failJob(vars: FailJobVariables): MutationPromise<FailJobData, FailJobVariables>;

interface FailJobRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: FailJobVariables): MutationRef<FailJobData, FailJobVariables>;
}
export const failJobRef: FailJobRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
failJob(dc: DataConnect, vars: FailJobVariables): MutationPromise<FailJobData, FailJobVariables>;

interface FailJobRef {
  ...
  (dc: DataConnect, vars: FailJobVariables): MutationRef<FailJobData, FailJobVariables>;
}
export const failJobRef: FailJobRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the failJobRef:
```typescript
const name = failJobRef.operationName;
console.log(name);
```

### Variables
The `failJob` mutation requires an argument of type `FailJobVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface FailJobVariables {
  id: UUIDString;
  error: string;
}
```
### Return Type
Recall that executing the `failJob` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `FailJobData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface FailJobData {
  videoJob_update?: VideoJob_Key | null;
}
```
### Using `failJob`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, failJob, FailJobVariables } from '@video-analyzer/dataconnect';

// The `failJob` mutation requires an argument of type `FailJobVariables`:
const failJobVars: FailJobVariables = {
  id: ..., 
  error: ..., 
};

// Call the `failJob()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await failJob(failJobVars);
// Variables can be defined inline as well.
const { data } = await failJob({ id: ..., error: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await failJob(dataConnect, failJobVars);

console.log(data.videoJob_update);

// Or, you can use the `Promise` API.
failJob(failJobVars).then((response) => {
  const data = response.data;
  console.log(data.videoJob_update);
});
```

### Using `failJob`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, failJobRef, FailJobVariables } from '@video-analyzer/dataconnect';

// The `failJob` mutation requires an argument of type `FailJobVariables`:
const failJobVars: FailJobVariables = {
  id: ..., 
  error: ..., 
};

// Call the `failJobRef()` function to get a reference to the mutation.
const ref = failJobRef(failJobVars);
// Variables can be defined inline as well.
const ref = failJobRef({ id: ..., error: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = failJobRef(dataConnect, failJobVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.videoJob_update);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.videoJob_update);
});
```

## recordJobEvent
You can execute the `recordJobEvent` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
recordJobEvent(vars: RecordJobEventVariables): MutationPromise<RecordJobEventData, RecordJobEventVariables>;

interface RecordJobEventRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: RecordJobEventVariables): MutationRef<RecordJobEventData, RecordJobEventVariables>;
}
export const recordJobEventRef: RecordJobEventRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
recordJobEvent(dc: DataConnect, vars: RecordJobEventVariables): MutationPromise<RecordJobEventData, RecordJobEventVariables>;

interface RecordJobEventRef {
  ...
  (dc: DataConnect, vars: RecordJobEventVariables): MutationRef<RecordJobEventData, RecordJobEventVariables>;
}
export const recordJobEventRef: RecordJobEventRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the recordJobEventRef:
```typescript
const name = recordJobEventRef.operationName;
console.log(name);
```

### Variables
The `recordJobEvent` mutation requires an argument of type `RecordJobEventVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface RecordJobEventVariables {
  jobId: UUIDString;
  eventType: string;
  agent?: string | null;
  details?: string | null;
}
```
### Return Type
Recall that executing the `recordJobEvent` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `RecordJobEventData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface RecordJobEventData {
  jobEvent_insert: JobEvent_Key;
}
```
### Using `recordJobEvent`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, recordJobEvent, RecordJobEventVariables } from '@video-analyzer/dataconnect';

// The `recordJobEvent` mutation requires an argument of type `RecordJobEventVariables`:
const recordJobEventVars: RecordJobEventVariables = {
  jobId: ..., 
  eventType: ..., 
  agent: ..., // optional
  details: ..., // optional
};

// Call the `recordJobEvent()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await recordJobEvent(recordJobEventVars);
// Variables can be defined inline as well.
const { data } = await recordJobEvent({ jobId: ..., eventType: ..., agent: ..., details: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await recordJobEvent(dataConnect, recordJobEventVars);

console.log(data.jobEvent_insert);

// Or, you can use the `Promise` API.
recordJobEvent(recordJobEventVars).then((response) => {
  const data = response.data;
  console.log(data.jobEvent_insert);
});
```

### Using `recordJobEvent`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, recordJobEventRef, RecordJobEventVariables } from '@video-analyzer/dataconnect';

// The `recordJobEvent` mutation requires an argument of type `RecordJobEventVariables`:
const recordJobEventVars: RecordJobEventVariables = {
  jobId: ..., 
  eventType: ..., 
  agent: ..., // optional
  details: ..., // optional
};

// Call the `recordJobEventRef()` function to get a reference to the mutation.
const ref = recordJobEventRef(recordJobEventVars);
// Variables can be defined inline as well.
const ref = recordJobEventRef({ jobId: ..., eventType: ..., agent: ..., details: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = recordJobEventRef(dataConnect, recordJobEventVars);

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

## deleteJobEmbeddings
You can execute the `deleteJobEmbeddings` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
deleteJobEmbeddings(vars: DeleteJobEmbeddingsVariables): MutationPromise<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;

interface DeleteJobEmbeddingsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: DeleteJobEmbeddingsVariables): MutationRef<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;
}
export const deleteJobEmbeddingsRef: DeleteJobEmbeddingsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
deleteJobEmbeddings(dc: DataConnect, vars: DeleteJobEmbeddingsVariables): MutationPromise<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;

interface DeleteJobEmbeddingsRef {
  ...
  (dc: DataConnect, vars: DeleteJobEmbeddingsVariables): MutationRef<DeleteJobEmbeddingsData, DeleteJobEmbeddingsVariables>;
}
export const deleteJobEmbeddingsRef: DeleteJobEmbeddingsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the deleteJobEmbeddingsRef:
```typescript
const name = deleteJobEmbeddingsRef.operationName;
console.log(name);
```

### Variables
The `deleteJobEmbeddings` mutation requires an argument of type `DeleteJobEmbeddingsVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface DeleteJobEmbeddingsVariables {
  jobId: UUIDString;
}
```
### Return Type
Recall that executing the `deleteJobEmbeddings` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `DeleteJobEmbeddingsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface DeleteJobEmbeddingsData {
  videoEmbedding_deleteMany: number;
}
```
### Using `deleteJobEmbeddings`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, deleteJobEmbeddings, DeleteJobEmbeddingsVariables } from '@video-analyzer/dataconnect';

// The `deleteJobEmbeddings` mutation requires an argument of type `DeleteJobEmbeddingsVariables`:
const deleteJobEmbeddingsVars: DeleteJobEmbeddingsVariables = {
  jobId: ..., 
};

// Call the `deleteJobEmbeddings()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await deleteJobEmbeddings(deleteJobEmbeddingsVars);
// Variables can be defined inline as well.
const { data } = await deleteJobEmbeddings({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await deleteJobEmbeddings(dataConnect, deleteJobEmbeddingsVars);

console.log(data.videoEmbedding_deleteMany);

// Or, you can use the `Promise` API.
deleteJobEmbeddings(deleteJobEmbeddingsVars).then((response) => {
  const data = response.data;
  console.log(data.videoEmbedding_deleteMany);
});
```

### Using `deleteJobEmbeddings`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, deleteJobEmbeddingsRef, DeleteJobEmbeddingsVariables } from '@video-analyzer/dataconnect';

// The `deleteJobEmbeddings` mutation requires an argument of type `DeleteJobEmbeddingsVariables`:
const deleteJobEmbeddingsVars: DeleteJobEmbeddingsVariables = {
  jobId: ..., 
};

// Call the `deleteJobEmbeddingsRef()` function to get a reference to the mutation.
const ref = deleteJobEmbeddingsRef(deleteJobEmbeddingsVars);
// Variables can be defined inline as well.
const ref = deleteJobEmbeddingsRef({ jobId: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = deleteJobEmbeddingsRef(dataConnect, deleteJobEmbeddingsVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.videoEmbedding_deleteMany);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.videoEmbedding_deleteMany);
});
```

