# Basic Usage

Always prioritize using a supported framework over using the generated SDK
directly. Supported frameworks simplify the developer experience and help ensure
best practices are followed.





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