# Basic Usage

Always prioritize using a supported framework over using the generated SDK
directly. Supported frameworks simplify the developer experience and help ensure
best practices are followed.




### React
For each operation, there is a wrapper hook that can be used to call the operation.

Here are all of the hooks that get generated:
```ts
import { useCreateExampleJob, useRecordExampleEvent, useDeleteExampleEvent, useListVideoJobs, useGetVideoJob, useListJobEvents, useListVideoEmbeddings, useListFailedJobs } from '@dataconnect/generated/react';
// The types of these hooks are available in react/index.d.ts

const { data, isPending, isSuccess, isError, error } = useCreateExampleJob(createExampleJobVars);

const { data, isPending, isSuccess, isError, error } = useRecordExampleEvent(recordExampleEventVars);

const { data, isPending, isSuccess, isError, error } = useDeleteExampleEvent(deleteExampleEventVars);

const { data, isPending, isSuccess, isError, error } = useListVideoJobs();

const { data, isPending, isSuccess, isError, error } = useGetVideoJob(getVideoJobVars);

const { data, isPending, isSuccess, isError, error } = useListJobEvents(listJobEventsVars);

const { data, isPending, isSuccess, isError, error } = useListVideoEmbeddings(listVideoEmbeddingsVars);

const { data, isPending, isSuccess, isError, error } = useListFailedJobs();

```

Here's an example from a different generated SDK:

```ts
import { useListAllMovies } from '@dataconnect/generated/react';

function MyComponent() {
  const { isLoading, data, error } = useListAllMovies();
  if(isLoading) {
    return <div>Loading...</div>
  }
  if(error) {
    return <div> An Error Occurred: {error} </div>
  }
}

// App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MyComponent from './my-component';

function App() {
  const queryClient = new QueryClient();
  return <QueryClientProvider client={queryClient}>
    <MyComponent />
  </QueryClientProvider>
}
```



## Advanced Usage
If a user is not using a supported framework, they can use the generated SDK directly.

Here's an example of how to use it with the first 5 operations:

```js
import { createExampleJob, recordExampleEvent, deleteExampleEvent, listVideoJobs, getVideoJob, listJobEvents, listVideoEmbeddings, listFailedJobs } from '@dataconnect/generated';


// Operation CreateExampleJob:  For variables, look at type CreateExampleJobVars in ../index.d.ts
const { data } = await CreateExampleJob(dataConnect, createExampleJobVars);

// Operation RecordExampleEvent:  For variables, look at type RecordExampleEventVars in ../index.d.ts
const { data } = await RecordExampleEvent(dataConnect, recordExampleEventVars);

// Operation DeleteExampleEvent:  For variables, look at type DeleteExampleEventVars in ../index.d.ts
const { data } = await DeleteExampleEvent(dataConnect, deleteExampleEventVars);

// Operation ListVideoJobs: 
const { data } = await ListVideoJobs(dataConnect);

// Operation GetVideoJob:  For variables, look at type GetVideoJobVars in ../index.d.ts
const { data } = await GetVideoJob(dataConnect, getVideoJobVars);

// Operation ListJobEvents:  For variables, look at type ListJobEventsVars in ../index.d.ts
const { data } = await ListJobEvents(dataConnect, listJobEventsVars);

// Operation ListVideoEmbeddings:  For variables, look at type ListVideoEmbeddingsVars in ../index.d.ts
const { data } = await ListVideoEmbeddings(dataConnect, listVideoEmbeddingsVars);

// Operation ListFailedJobs: 
const { data } = await ListFailedJobs(dataConnect);


```