# Basic Usage

Always prioritize using a supported framework over using the generated SDK
directly. Supported frameworks simplify the developer experience and help ensure
best practices are followed.





## Advanced Usage
If a user is not using a supported framework, they can use the generated SDK directly.

Here's an example of how to use it with the first 5 operations:

```js
import { createVideoJob, updateJobStatus, completeJob, failJob, recordJobEvent, getJob, listJobs, getJobEvents, listEmbeddings, getJobEmbeddings } from '@video-analyzer/dataconnect';


// Operation createVideoJob:  For variables, look at type CreateVideoJobVars in ../index.d.ts
const { data } = await CreateVideoJob(dataConnect, createVideoJobVars);

// Operation updateJobStatus:  For variables, look at type UpdateJobStatusVars in ../index.d.ts
const { data } = await UpdateJobStatus(dataConnect, updateJobStatusVars);

// Operation completeJob:  For variables, look at type CompleteJobVars in ../index.d.ts
const { data } = await CompleteJob(dataConnect, completeJobVars);

// Operation failJob:  For variables, look at type FailJobVars in ../index.d.ts
const { data } = await FailJob(dataConnect, failJobVars);

// Operation recordJobEvent:  For variables, look at type RecordJobEventVars in ../index.d.ts
const { data } = await RecordJobEvent(dataConnect, recordJobEventVars);

// Operation getJob:  For variables, look at type GetJobVars in ../index.d.ts
const { data } = await GetJob(dataConnect, getJobVars);

// Operation listJobs:  For variables, look at type ListJobsVars in ../index.d.ts
const { data } = await ListJobs(dataConnect, listJobsVars);

// Operation getJobEvents:  For variables, look at type GetJobEventsVars in ../index.d.ts
const { data } = await GetJobEvents(dataConnect, getJobEventsVars);

// Operation listEmbeddings:  For variables, look at type ListEmbeddingsVars in ../index.d.ts
const { data } = await ListEmbeddings(dataConnect, listEmbeddingsVars);

// Operation getJobEmbeddings:  For variables, look at type GetJobEmbeddingsVars in ../index.d.ts
const { data } = await GetJobEmbeddings(dataConnect, getJobEmbeddingsVars);


```