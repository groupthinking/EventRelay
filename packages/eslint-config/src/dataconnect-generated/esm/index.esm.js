import { queryRef, executeQuery, mutationRef, executeMutation, validateArgs } from 'firebase/data-connect';

export const connectorConfig = {
  connector: 'example',
  service: 'eventrelay',
  location: 'us-east4'
};

export const createExampleJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'CreateExampleJob', inputVars);
}
createExampleJobRef.operationName = 'CreateExampleJob';

export function createExampleJob(dcOrVars, vars) {
  return executeMutation(createExampleJobRef(dcOrVars, vars));
}

export const recordExampleEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'RecordExampleEvent', inputVars);
}
recordExampleEventRef.operationName = 'RecordExampleEvent';

export function recordExampleEvent(dcOrVars, vars) {
  return executeMutation(recordExampleEventRef(dcOrVars, vars));
}

export const deleteExampleEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'DeleteExampleEvent', inputVars);
}
deleteExampleEventRef.operationName = 'DeleteExampleEvent';

export function deleteExampleEvent(dcOrVars, vars) {
  return executeMutation(deleteExampleEventRef(dcOrVars, vars));
}

export const listVideoJobsRef = (dc) => {
  const { dc: dcInstance} = validateArgs(connectorConfig, dc, undefined);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListVideoJobs');
}
listVideoJobsRef.operationName = 'ListVideoJobs';

export function listVideoJobs(dc) {
  return executeQuery(listVideoJobsRef(dc));
}

export const getVideoJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'GetVideoJob', inputVars);
}
getVideoJobRef.operationName = 'GetVideoJob';

export function getVideoJob(dcOrVars, vars) {
  return executeQuery(getVideoJobRef(dcOrVars, vars));
}

export const listJobEventsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListJobEvents', inputVars);
}
listJobEventsRef.operationName = 'ListJobEvents';

export function listJobEvents(dcOrVars, vars) {
  return executeQuery(listJobEventsRef(dcOrVars, vars));
}

export const listVideoEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListVideoEmbeddings', inputVars);
}
listVideoEmbeddingsRef.operationName = 'ListVideoEmbeddings';

export function listVideoEmbeddings(dcOrVars, vars) {
  return executeQuery(listVideoEmbeddingsRef(dcOrVars, vars));
}

export const listFailedJobsRef = (dc) => {
  const { dc: dcInstance} = validateArgs(connectorConfig, dc, undefined);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListFailedJobs');
}
listFailedJobsRef.operationName = 'ListFailedJobs';

export function listFailedJobs(dc) {
  return executeQuery(listFailedJobsRef(dc));
}

