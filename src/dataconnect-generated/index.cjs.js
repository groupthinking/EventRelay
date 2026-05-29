const { queryRef, executeQuery, validateArgsWithOptions, mutationRef, executeMutation, validateArgs } = require('firebase/data-connect');

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
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(createVideoJobRef(dcInstance, inputVars));
}
;

const updateJobStatusRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'updateJobStatus', inputVars);
}
updateJobStatusRef.operationName = 'updateJobStatus';
exports.updateJobStatusRef = updateJobStatusRef;

exports.updateJobStatus = function updateJobStatus(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(updateJobStatusRef(dcInstance, inputVars));
}
;

const completeJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'completeJob', inputVars);
}
completeJobRef.operationName = 'completeJob';
exports.completeJobRef = completeJobRef;

exports.completeJob = function completeJob(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(completeJobRef(dcInstance, inputVars));
}
;

const failJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'failJob', inputVars);
}
failJobRef.operationName = 'failJob';
exports.failJobRef = failJobRef;

exports.failJob = function failJob(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(failJobRef(dcInstance, inputVars));
}
;

const recordJobEventRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'recordJobEvent', inputVars);
}
recordJobEventRef.operationName = 'recordJobEvent';
exports.recordJobEventRef = recordJobEventRef;

exports.recordJobEvent = function recordJobEvent(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(recordJobEventRef(dcInstance, inputVars));
}
;

const getJobRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJob', inputVars);
}
getJobRef.operationName = 'getJob';
exports.getJobRef = getJobRef;

exports.getJob = function getJob(dcOrVars, varsOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrVars, varsOrOptions, options, true, true);
  return executeQuery(getJobRef(dcInstance, inputVars), inputOpts && inputOpts.fetchPolicy);
}
;

const listJobsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'listJobs', inputVars);
}
listJobsRef.operationName = 'listJobs';
exports.listJobsRef = listJobsRef;

exports.listJobs = function listJobs(dcOrVars, varsOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrVars, varsOrOptions, options, true, false);
  return executeQuery(listJobsRef(dcInstance, inputVars), inputOpts && inputOpts.fetchPolicy);
}
;

const getJobEventsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJobEvents', inputVars);
}
getJobEventsRef.operationName = 'getJobEvents';
exports.getJobEventsRef = getJobEventsRef;

exports.getJobEvents = function getJobEvents(dcOrVars, varsOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrVars, varsOrOptions, options, true, true);
  return executeQuery(getJobEventsRef(dcInstance, inputVars), inputOpts && inputOpts.fetchPolicy);
}
;

const listEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'listEmbeddings', inputVars);
}
listEmbeddingsRef.operationName = 'listEmbeddings';
exports.listEmbeddingsRef = listEmbeddingsRef;

exports.listEmbeddings = function listEmbeddings(dcOrVars, varsOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrVars, varsOrOptions, options, true, false);
  return executeQuery(listEmbeddingsRef(dcInstance, inputVars), inputOpts && inputOpts.fetchPolicy);
}
;

const getJobEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'getJobEmbeddings', inputVars);
}
getJobEmbeddingsRef.operationName = 'getJobEmbeddings';
exports.getJobEmbeddingsRef = getJobEmbeddingsRef;

exports.getJobEmbeddings = function getJobEmbeddings(dcOrVars, varsOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrVars, varsOrOptions, options, true, true);
  return executeQuery(getJobEmbeddingsRef(dcInstance, inputVars), inputOpts && inputOpts.fetchPolicy);
}
;

const deleteJobEmbeddingsRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'deleteJobEmbeddings', inputVars);
}
deleteJobEmbeddingsRef.operationName = 'deleteJobEmbeddings';
exports.deleteJobEmbeddingsRef = deleteJobEmbeddingsRef;

exports.deleteJobEmbeddings = function deleteJobEmbeddings(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(deleteJobEmbeddingsRef(dcInstance, inputVars));
}
;
