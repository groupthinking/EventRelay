const { queryRef, executeQuery, mutationRef, executeMutation, validateArgs } = require('firebase/data-connect');

const connectorConfig = {
  connector: 'jobs',
  service: 'eventrelay',
  location: 'us-east4'
};
exports.connectorConfig = connectorConfig;

const createVideoJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'createVideoJob', inputVars);
}
createVideoJobRef.operationName = 'createVideoJob';
exports.createVideoJobRef = createVideoJobRef;

exports.createVideoJob = function createVideoJob(dcOrVars, vars) {
  return executeMutation(createVideoJobRef(dcOrVars, vars));
};

const updateJobStatusRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'updateJobStatus', inputVars);
}
updateJobStatusRef.operationName = 'updateJobStatus';
exports.updateJobStatusRef = updateJobStatusRef;

exports.updateJobStatus = function updateJobStatus(dcOrVars, vars) {
  return executeMutation(updateJobStatusRef(dcOrVars, vars));
};

const completeJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'completeJob', inputVars);
}
completeJobRef.operationName = 'completeJob';
exports.completeJobRef = completeJobRef;

exports.completeJob = function completeJob(dcOrVars, vars) {
  return executeMutation(completeJobRef(dcOrVars, vars));
};

const failJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'failJob', inputVars);
}
failJobRef.operationName = 'failJob';
exports.failJobRef = failJobRef;

exports.failJob = function failJob(dcOrVars, vars) {
  return executeMutation(failJobRef(dcOrVars, vars));
};

const recordJobEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'recordJobEvent', inputVars);
}
recordJobEventRef.operationName = 'recordJobEvent';
exports.recordJobEventRef = recordJobEventRef;

exports.recordJobEvent = function recordJobEvent(dcOrVars, vars) {
  return executeMutation(recordJobEventRef(dcOrVars, vars));
};

const getJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJob', inputVars);
}
getJobRef.operationName = 'getJob';
exports.getJobRef = getJobRef;

exports.getJob = function getJob(dcOrVars, vars) {
  return executeQuery(getJobRef(dcOrVars, vars));
};

const listJobsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'listJobs', inputVars);
}
listJobsRef.operationName = 'listJobs';
exports.listJobsRef = listJobsRef;

exports.listJobs = function listJobs(dcOrVars, vars) {
  return executeQuery(listJobsRef(dcOrVars, vars));
};

const getJobEventsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJobEvents', inputVars);
}
getJobEventsRef.operationName = 'getJobEvents';
exports.getJobEventsRef = getJobEventsRef;

exports.getJobEvents = function getJobEvents(dcOrVars, vars) {
  return executeQuery(getJobEventsRef(dcOrVars, vars));
};

const listEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'listEmbeddings', inputVars);
}
listEmbeddingsRef.operationName = 'listEmbeddings';
exports.listEmbeddingsRef = listEmbeddingsRef;

exports.listEmbeddings = function listEmbeddings(dcOrVars, vars) {
  return executeQuery(listEmbeddingsRef(dcOrVars, vars));
};

const getJobEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJobEmbeddings', inputVars);
}
getJobEmbeddingsRef.operationName = 'getJobEmbeddings';
exports.getJobEmbeddingsRef = getJobEmbeddingsRef;

exports.getJobEmbeddings = function getJobEmbeddings(dcOrVars, vars) {
  return executeQuery(getJobEmbeddingsRef(dcOrVars, vars));
};

const deleteJobEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'deleteJobEmbeddings', inputVars);
}
deleteJobEmbeddingsRef.operationName = 'deleteJobEmbeddings';
exports.deleteJobEmbeddingsRef = deleteJobEmbeddingsRef;

exports.deleteJobEmbeddings = function deleteJobEmbeddings(dcOrVars, vars) {
  return executeMutation(deleteJobEmbeddingsRef(dcOrVars, vars));
};
