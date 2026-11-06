/** Combined route smoke test: local-only mode never executes originals.
 * Uses the actual route, Node bridge and Python journal; provider/auth are stubs.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const root = resolve(import.meta.dirname, '..');
const python = execFileSync('python3', ['-c', 'import sys; print(sys.executable)'], {encoding:'utf8'}).trim();
const state = globalThis.__relayRouteTest = { calls: [], identity: 'test@example.invalid' };
const action = {tool:'create_workflow_task',input:{title:'Review target'},status:'pending',
  result:'Prepared for review. No tool has been executed.',isError:false};
const modules = {
  'next/server': 'export const NextResponse = {json: (body,init) => Response.json(body,init)};',
  'server-only': 'export {};',
  '@/lib/action-agent': `export const AVAILABLE_TOOL_NAMES=['create_workflow_task']; export async function runActionAgent(options){globalThis.__relayRouteTest.calls.push(['model',options]);return {provider:'test',actions:[{tool:'create_workflow_task',input:{title:'Review target'},status:'pending',result:'Prepared for review. No tool has been executed.',isError:false}]};} export async function executePreparedActions(options){globalThis.__relayRouteTest.calls.push(['execute',options]);throw Error('must not execute');}`,
  '@/lib/workflow-task-store': 'export async function workflowTaskOwner(){return null;} export async function readWorkflowTask(){return null;}',
  '@/lib/workflow-task-preview': 'export function issueWorkflowTaskPreview(){throw Error("must not issue executable token");} export function verifyWorkflowTaskPreview(){return false;}',
  '@/lib/gemini-client': 'export const hasGeminiKey=()=>true;',
  '@/lib/billing/billing-context': 'export async function resolveTrustedBillingEmail(){return globalThis.__relayRouteTest.identity;}',
  '@/lib/billing/entitlement-store': 'export async function isProSubscriber(){return false;}',
};
registerHooks({resolve(specifier, context, nextResolve) {
  if (specifier in modules) return {url:'data:text/javascript,'+encodeURIComponent(modules[specifier]),shortCircuit:true};
  if (specifier.startsWith('@/')) {
    const relative = specifier.slice(2);
    return {url:pathToFileURL(join(root,'apps/web/src',relative.endsWith('.mjs') ? relative : relative+'.ts')).href,shortCircuit:true};
  }
  return nextResolve(specifier,context);
}});
const { POST } = await import('../apps/web/src/app/api/agents/actions/route.ts');
const envKeys = ['RELAY_REVIEW_JOURNAL_MODE','RELAY_REVIEW_STATE_DIRECTORY','RELAY_REVIEW_SCRIPTS_DIRECTORY','RELAY_REVIEW_PYTHON_EXECUTABLE','VERCEL','AWS_LAMBDA_FUNCTION_NAME','K_SERVICE'];
function reset() { for (const key of envKeys) delete process.env[key];state.calls=[];state.identity='test@example.invalid'; }
function enable(dir) {
  process.env.RELAY_REVIEW_JOURNAL_MODE='local-review-only';
  process.env.RELAY_REVIEW_STATE_DIRECTORY=join(dir,'state');
  process.env.RELAY_REVIEW_SCRIPTS_DIRECTORY=join(root,'scripts');
  process.env.RELAY_REVIEW_PYTHON_EXECUTABLE=python;
}
function request(body) {return new Request('http://localhost/api/agents/actions',
  {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});}

test('combined route returns exact stored preview with verified local receipt and no confirmation token', async () => {
  reset(); const dir=await mkdtemp(join(tmpdir(),'relay-integrated-'));enable(dir);
  try {
    const response=await POST(request({mode:'preview',transcript:'A sufficiently long transcript for review'}));
    const body=await response.json();
    assert.equal(response.status,200);
    assert.deepEqual(body.actions,[action]);
    assert.equal(body.confirmationToken,undefined);
    assert.equal(body.localArtifactReceipt.artifactVerified,true);
    assert.equal(body.localArtifactReceipt.originalActionsExecuted,false);
    assert.equal(body.localArtifactReceipt.originalTaskComplete,false);
    const artifactBytes=await readFile(join(dir,'state','artifacts',body.localArtifactReceipt.taskId+'.txt'));
    const artifact=JSON.parse(artifactBytes);
    assert.deepEqual(artifact.actions,body.actions);
    assert.equal(createHash('sha256').update(artifactBytes).digest('hex'),body.localArtifactReceipt.artifactHash);
    assert.deepEqual(state.calls.map(c=>c[0]),['model']);
    assert.equal(state.calls[0][1].executeTools,false);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});
test('combined route denies execute even with fabricated signed confirmation', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-integrated-'));enable(dir);
  try {
    const response=await POST(request({mode:'execute',actions:[action],jobId:'preview_fake',confirmationToken:'forged'}));
    assert.equal(response.status,409);assert.deepEqual(state.calls,[]);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});
test('combined route requires trusted identity and fails closed', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-integrated-'));enable(dir);
  try {
    state.identity=null;
    assert.equal((await POST(request({transcript:'A sufficiently long transcript for review'}))).status,401);
    assert.deepEqual(state.calls,[]);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});
