import { queryRef, executeQuery, mutationRef, executeMutation, validateArgs } from 'firebase/data-connect';

export const connectorConfig = {
  connector: 'jobs',
  service: 'eventrelay',
  location: 'us-east4'
};

export const createVideoJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'createVideoJob', inputVars);
}
createVideoJobRef.operationName = 'createVideoJob';

export function createVideoJob(dcOrVars, vars) {
  return executeMutation(createVideoJobRef(dcOrVars, vars));
}

export const updateJobStatusRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'updateJobStatus', inputVars);
}
updateJobStatusRef.operationName = 'updateJobStatus';

export function updateJobStatus(dcOrVars, vars) {
  return executeMutation(updateJobStatusRef(dcOrVars, vars));
}

export const completeJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'completeJob', inputVars);
}
completeJobRef.operationName = 'completeJob';

export function completeJob(dcOrVars, vars) {
  return executeMutation(completeJobRef(dcOrVars, vars));
}

export const failJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'failJob', inputVars);
}
failJobRef.operationName = 'failJob';

export function failJob(dcOrVars, vars) {
  return executeMutation(failJobRef(dcOrVars, vars));
}

export const recordJobEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'recordJobEvent', inputVars);
}
recordJobEventRef.operationName = 'recordJobEvent';

export function recordJobEvent(dcOrVars, vars) {
  return executeMutation(recordJobEventRef(dcOrVars, vars));
}

export const getJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJob', inputVars);
}
getJobRef.operationName = 'getJob';

export function getJob(dcOrVars, vars) {
  return executeQuery(getJobRef(dcOrVars, vars));
}

export const listJobsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'listJobs', inputVars);
}
listJobsRef.operationName = 'listJobs';

export function listJobs(dcOrVars, vars) {
  return executeQuery(listJobsRef(dcOrVars, vars));
}

export const getJobEventsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJobEvents', inputVars);
}
getJobEventsRef.operationName = 'getJobEvents';

export function getJobEvents(dcOrVars, vars) {
  return executeQuery(getJobEventsRef(dcOrVars, vars));
}

export const listEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'listEmbeddings', inputVars);
}
listEmbeddingsRef.operationName = 'listEmbeddings';

export function listEmbeddings(dcOrVars, vars) {
  return executeQuery(listEmbeddingsRef(dcOrVars, vars));
}

export const getJobEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJobEmbeddings', inputVars);
}
getJobEmbeddingsRef.operationName = 'getJobEmbeddings';

export function getJobEmbeddings(dcOrVars, vars) {
  return executeQuery(getJobEmbeddingsRef(dcOrVars, vars));
}

export const deleteJobEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'deleteJobEmbeddings', inputVars);
}
deleteJobEmbeddingsRef.operationName = 'deleteJobEmbeddings';

export function deleteJobEmbeddings(dcOrVars, vars) {
  return executeMutation(deleteJobEmbeddingsRef(dcOrVars, vars));
}

