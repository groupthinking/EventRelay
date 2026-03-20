const { queryRef, executeQuery, mutationRef, executeMutation, validateArgs } = require('firebase/data-connect');

const connectorConfig = {
  connector: 'example',
  service: 'eventrelay',
  location: 'us-east4'
};
exports.connectorConfig = connectorConfig;

const listVideoJobsRef = (dc) => {
  const { dc: dcInstance} = validateArgs(connectorConfig, dc, undefined);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListVideoJobs');
}
listVideoJobsRef.operationName = 'ListVideoJobs';
exports.listVideoJobsRef = listVideoJobsRef;

exports.listVideoJobs = function listVideoJobs(dc) {
  return executeQuery(listVideoJobsRef(dc));
};

const getVideoJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'GetVideoJob', inputVars);
}
getVideoJobRef.operationName = 'GetVideoJob';
exports.getVideoJobRef = getVideoJobRef;

exports.getVideoJob = function getVideoJob(dcOrVars, vars) {
  return executeQuery(getVideoJobRef(dcOrVars, vars));
};

const listJobEventsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListJobEvents', inputVars);
}
listJobEventsRef.operationName = 'ListJobEvents';
exports.listJobEventsRef = listJobEventsRef;

exports.listJobEvents = function listJobEvents(dcOrVars, vars) {
  return executeQuery(listJobEventsRef(dcOrVars, vars));
};

const listVideoEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListVideoEmbeddings', inputVars);
}
listVideoEmbeddingsRef.operationName = 'ListVideoEmbeddings';
exports.listVideoEmbeddingsRef = listVideoEmbeddingsRef;

exports.listVideoEmbeddings = function listVideoEmbeddings(dcOrVars, vars) {
  return executeQuery(listVideoEmbeddingsRef(dcOrVars, vars));
};

const listFailedJobsRef = (dc) => {
  const { dc: dcInstance} = validateArgs(connectorConfig, dc, undefined);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListFailedJobs');
}
listFailedJobsRef.operationName = 'ListFailedJobs';
exports.listFailedJobsRef = listFailedJobsRef;

exports.listFailedJobs = function listFailedJobs(dc) {
  return executeQuery(listFailedJobsRef(dc));
};

const createExampleJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'CreateExampleJob', inputVars);
}
createExampleJobRef.operationName = 'CreateExampleJob';
exports.createExampleJobRef = createExampleJobRef;

exports.createExampleJob = function createExampleJob(dcOrVars, vars) {
  return executeMutation(createExampleJobRef(dcOrVars, vars));
};

const recordExampleEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'RecordExampleEvent', inputVars);
}
recordExampleEventRef.operationName = 'RecordExampleEvent';
exports.recordExampleEventRef = recordExampleEventRef;

exports.recordExampleEvent = function recordExampleEvent(dcOrVars, vars) {
  return executeMutation(recordExampleEventRef(dcOrVars, vars));
};

const deleteExampleEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'DeleteExampleEvent', inputVars);
}
deleteExampleEventRef.operationName = 'DeleteExampleEvent';
exports.deleteExampleEventRef = deleteExampleEventRef;

exports.deleteExampleEvent = function deleteExampleEvent(dcOrVars, vars) {
  return executeMutation(deleteExampleEventRef(dcOrVars, vars));
};
