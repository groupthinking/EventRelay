/** Actual route integration with provider/auth stubs, real local Python effects.
 * No credentials, LLM/network requests, or production storage are used.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { registerHooks } from 'node:module';
import { mkdtemp, rm, readFile, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = resolve(import.meta.dirname, '..');
const python = execFileSync('python3', ['-c', 'import sys; print(sys.executable)'], {encoding:'utf8'}).trim();
const state = globalThis.__relayRouteTest = { calls: [], identity: 'test@example.invalid', actions: [], pro: false };
const modules = {
  'next/server': 'export const NextResponse = {json: (body,init) => Response.json(body,init)};',
  'server-only': 'export {};',
  '@/lib/action-agent': `export const AVAILABLE_TOOL_NAMES=['create_workflow_task','dispatch_agent']; export async function runActionAgent(options){globalThis.__relayRouteTest.calls.push(['model',options]);return {provider:'test-provider',actions:globalThis.__relayRouteTest.actions};} export async function executePreparedActions(options){globalThis.__relayRouteTest.calls.push(['execute',options]);return options.actions.map(x=>({...x,status:'fulfilled'}));}`,
  '@/lib/gemini-client': 'export const hasGeminiKey=()=>true;',
  '@/lib/billing/billing-context': 'export async function resolveTrustedBillingEmail(){return globalThis.__relayRouteTest.identity;}',
  '@/lib/billing/entitlement-store': 'export async function isProSubscriber(){return globalThis.__relayRouteTest.pro;}',
};
registerHooks({resolve(specifier, context, nextResolve) {
  if (specifier in modules) return {url:'data:text/javascript,'+encodeURIComponent(modules[specifier]),shortCircuit:true};
  if (specifier.startsWith('@/')) {
    const relative = specifier.slice(2);
    const path = join(root,'apps/web/src',relative.endsWith('.mjs') ? relative : relative+'.ts');
    return {url:pathToFileURL(path).href,shortCircuit:true};
  }
  return nextResolve(specifier,context);
}});
const { POST } = await import('../apps/web/src/app/api/agents/actions/route.ts');
const { resolveActionReviewJournal } = await import('../apps/web/src/lib/action-review-journal.mjs');
const { createLocalReviewBridge } = await import('../apps/web/src/lib/relay-local-review.mjs');
const action = {tool:'create_workflow_task',input:{title:'Review target'},status:'pending',result:'Prepared for review. No tool has been executed.',isError:false};
function request(body) { return new Request('http://localhost/api/agents/actions',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}); }
const keys = ['RELAY_REVIEW_JOURNAL_MODE','RELAY_REVIEW_STATE_DIRECTORY','RELAY_REVIEW_SCRIPTS_DIRECTORY','RELAY_REVIEW_PYTHON_EXECUTABLE','VERCEL','AWS_LAMBDA_FUNCTION_NAME','K_SERVICE'];
function reset() {
  for (const key of keys) delete process.env[key];
  state.calls=[];state.identity='test@example.invalid';state.actions=[structuredClone(action)];state.pro=false;
}
function enable(directory) {
  process.env.RELAY_REVIEW_JOURNAL_MODE='local-review-only';
  process.env.RELAY_REVIEW_STATE_DIRECTORY=join(directory,'state');
  process.env.RELAY_REVIEW_SCRIPTS_DIRECTORY=join(root,'scripts');
  process.env.RELAY_REVIEW_PYTHON_EXECUTABLE=python;
}

test('actual review route integrates durable artifact and actor-scoped replay without executing originals', async () => {
  reset(); const dir=await mkdtemp(join(tmpdir(),'relay-route-'));enable(dir);
  try {
    const first=await POST(request({transcript:'A sufficiently long transcript for review',jobId:'untrusted-job'}));
    const body=await first.json();assert.equal(first.status,200);
    assert.deepEqual(body.actions,[action]);assert.equal(body.localArtifactReceipt.originalActionsExecuted,false);
    assert.equal(body.localArtifactReceipt.originalTaskComplete,false);assert.equal(body.localArtifactReceipt.artifactVerified,true);
    assert.deepEqual(state.calls.map(c=>c[0]),['model']);assert.equal(state.calls[0][1].executeTools,false);
    const repeated=await (await POST(request({transcript:'Another prompt; same exact plan',jobId:'changed-job'}))).json();
    assert.equal(repeated.localArtifactReceipt.taskId,body.localArtifactReceipt.taskId);
    assert.equal(repeated.localArtifactReceipt.historyHead,body.localArtifactReceipt.historyHead);
    state.identity='another@example.invalid';
    const other=await (await POST(request({transcript:'Another authenticated user'}))).json();
    assert.notEqual(other.localArtifactReceipt.taskId,body.localArtifactReceipt.taskId);
    const artifactBytes=await readFile(join(dir,'state','artifacts',body.localArtifactReceipt.taskId+'.txt'));
    const artifact=JSON.parse(artifactBytes);
    assert.equal(createHash('sha256').update(artifactBytes).digest('hex'),body.localArtifactReceipt.artifactHash);
    assert.deepEqual(artifact.actions,body.actions);
    assert.equal(artifact.original_actions_executed,false);assert.deepEqual(artifact.actions,[action]);
  } finally { reset();await rm(dir,{recursive:true,force:true}); }
});

test('local mode refuses execute before any model/tool call, ignoring request-supplied permissions and paths', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-route-'));enable(dir);
  try {
    const response=await POST(request({mode:'execute',actions:[action],approved:true,RELAY_REVIEW_JOURNAL_MODE:'disabled',stateDirectory:'/tmp/forged'}));
    assert.equal(response.status,409);assert.deepEqual(state.calls,[]);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});

test('missing identity/config, invalid mode and serverless hosts fail before model calls', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-route-'));enable(dir);
  try {
    state.identity=null;assert.equal((await POST(request({transcript:'Long enough review transcript',email:'forged@example.invalid'}))).status,401);
    state.identity='test@example.invalid';delete process.env.RELAY_REVIEW_PYTHON_EXECUTABLE;
    assert.equal((await POST(request({transcript:'Long enough review transcript'}))).status,503);
    enable(dir);process.env.RELAY_REVIEW_JOURNAL_MODE='typo';
    assert.equal((await POST(request({transcript:'Long enough review transcript'}))).status,503);
    enable(dir);process.env.VERCEL='1';
    assert.equal((await POST(request({transcript:'Long enough review transcript'}))).status,503);
    assert.deepEqual(state.calls,[]);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});

test('journal failure does not fall back to ephemeral success or expose internal paths', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-route-'));enable(dir);
  try {
    process.env.RELAY_REVIEW_PYTHON_EXECUTABLE=join(dir,'nonexistent-private-python');
    const response=await POST(request({transcript:'Long enough review transcript'}));const body=await response.json();
    assert.equal(response.status,502);assert.equal(body.success,false);assert.deepEqual(body.actions,[]);
    assert.equal(body.error,'Internal server error');assert.equal(JSON.stringify(body).includes(dir),false);
    assert.deepEqual(state.calls.map(c=>c[0]),['model']);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});

test('empty review plan persists honestly; nonpending model action fails rather than pretending execution', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-route-'));enable(dir);
  try {
    state.actions=[];
    const empty=await POST(request({transcript:'Nothing actionable in this transcript'}));const body=await empty.json();
    assert.equal(empty.status,200);assert.equal(body.localArtifactReceipt.originalTaskComplete,false);assert.deepEqual(body.actions,[]);
    state.actions=[{...action,status:'fulfilled'}];
    const bad=await POST(request({transcript:'Long enough review transcript'}));assert.equal(bad.status,502);
    assert.ok(state.calls.every(c=>c[0]==='model'));
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});

test('disabled integration preserves preview and existing execute behavior; body cannot enable it', async () => {
  reset();
  let response=await POST(request({transcript:'Long enough review transcript',RELAY_REVIEW_JOURNAL_MODE:'local-review-only'}));
  let body=await response.json();assert.equal(response.status,200);assert.equal(body.localArtifactReceipt,undefined);
  assert.equal(state.calls[0][1].executeTools,false);
  response=await POST(request({mode:'execute',actions:[action]}));body=await response.json();
  assert.equal(response.status,200);assert.equal(body.provider,'confirmed-plan');assert.equal(body.actions[0].status,'fulfilled');
  assert.equal(state.calls.at(-1)[0],'execute');
  assert.equal((await POST(request(null))).status,400);
});

test('forged server config and unverified artifact cannot yield verified receipt', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-route-'));enable(dir);
  try {
    const journal=resolveActionReviewJournal();
    const receipt=await journal.persist([action],'test@example.invalid');
    const { writeFile }=await import('node:fs/promises');
    await writeFile(join(dir,'state','artifacts',receipt.taskId+'.txt'),'tampered');
    await assert.rejects(journal.persist([action],'test@example.invalid'),/did not verify/);
    assert.equal((await readdir(join(dir,'state','artifacts'))).length,1);
    await assert.rejects(journal.persist([action],null),/Trusted identity/);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});

// Reproduce the original v1 adapter's exact lossy serialization, rather than
// seeding through the repaired adapter. All data is synthetic and local.
function legacyReviewKey(actions, identity) {
  const actorHash=createHash('sha256').update(identity).digest('hex');
  return 'review-v1-'+createHash('sha256').update(JSON.stringify({actorHash,actions})).digest('hex');
}
function seedLegacyReview(directory, actions, identity, complete=true) {
  const key=legacyReviewKey(actions,identity);
  const script=`
import json, sys
from relay_harness.core import Harness, artifact_contract
actions = json.loads(sys.argv[3])
body = {
    "source": "EventRelay review-only AgentAction[]",
    "original_actions_executed": False,
    "original_task_complete": False,
    "actions": [{"tool": a["tool"], "input": a["input"], "status": "pending"} for a in actions],
    "next_step": "A trusted host must resolve user intent, permissions and a supported effect adapter before execution.",
}
content = json.dumps(body, indent=2, ensure_ascii=False, allow_nan=False) + "\\n"
h = Harness(sys.argv[1])
task = h.submit(artifact_contract(sys.argv[2], "Persist an exact local review plan, not execute its actions", content, contains=['"original_actions_executed": false']))
receipt = h.run(task) if sys.argv[4] == 'complete' else h.receipt(task)
print(json.dumps({"taskId": task, "receipt": receipt}))
h.close()
`;
  return JSON.parse(execFileSync(python,['-c',script,join(directory,'state'),key,JSON.stringify(actions),complete?'complete':'pending'],{
    encoding:'utf8',env:{PYTHONPATH:join(root,'scripts'),PYTHONUTF8:'1'},
  }));
}

test('journal upgrade preserves legacy evidence and retries one exact v2 artifact', async () => {
  for (const {optional,complete} of [
    {optional:{result:'Prepared task for review',isError:false},complete:true},
    {optional:{},complete:true},
    {optional:{result:'Prepared task for review',isError:false},complete:false},
  ]) {
    reset();const dir=await mkdtemp(join(tmpdir(),'relay-upgrade-'));enable(dir);
    try {
      const actions=[{tool:action.tool,input:action.input,status:action.status,...optional}];const identity='upgrade@example.invalid';
      const legacy=seedLegacyReview(dir,actions,identity,complete);
      const oldPath=join(dir,'state','artifacts',legacy.taskId+'.txt');
      const oldBytes=complete?await readFile(oldPath):null;
      const bridge=createLocalReviewBridge({stateDirectory:join(dir,'state'),scriptsDirectory:join(root,'scripts'),pythonExecutable:python});
      const journal=resolveActionReviewJournal();
      const receipts=await Promise.all(Array.from({length:3},()=>journal.persist(actions,identity)));
      const current=receipts[0];
      const expectedKey=legacyReviewKey(actions,identity).replace('review-v1-','review-v2-');
      assert.equal(current.taskId,createHash('sha256').update(expectedKey).digest('hex').slice(0,32));
      assert.notEqual(current.taskId,legacy.taskId);
      assert.deepEqual(receipts,[current,current,current]);
      assert.deepEqual(await resolveActionReviewJournal().persist(actions,identity),current);
      assert.equal(current.originalActionsExecuted,false);assert.equal(current.originalTaskComplete,false);
      const saved=JSON.parse(await readFile(join(dir,'state','artifacts',current.taskId+'.txt'),'utf8'));
      assert.deepEqual(saved.actions,actions);
      assert.deepEqual(await bridge.receipt(legacy.taskId),legacy.receipt);
      if (complete) assert.deepEqual(await readFile(oldPath),oldBytes);
      else await assert.rejects(readFile(oldPath),{code:'ENOENT'});
      assert.equal((await readdir(join(dir,'state','artifacts'))).length,complete?2:1);
    } finally {reset();await rm(dir,{recursive:true,force:true});}
  }
});

test('direct legacy-key conflicts remain fail-closed and never rewrite old evidence', async () => {
  reset();const dir=await mkdtemp(join(tmpdir(),'relay-upgrade-'));enable(dir);
  try {
    const actions=[{...action,result:'Prepared task for review',isError:false}];
    const identity='upgrade@example.invalid';const legacy=seedLegacyReview(dir,actions,identity);
    const oldPath=join(dir,'state','artifacts',legacy.taskId+'.txt');const oldBytes=await readFile(oldPath);
    const bridge=createLocalReviewBridge({stateDirectory:join(dir,'state'),scriptsDirectory:join(root,'scripts'),pythonExecutable:python});
    await assert.rejects(bridge.persistReview(actions,legacyReviewKey(actions,identity)));
    assert.deepEqual(await readFile(oldPath),oldBytes);
    assert.deepEqual(await bridge.receipt(legacy.taskId),legacy.receipt);
    assert.equal((await readdir(join(dir,'state','artifacts'))).length,1);
  } finally {reset();await rm(dir,{recursive:true,force:true});}
});
