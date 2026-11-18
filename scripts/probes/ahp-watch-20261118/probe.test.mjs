import test from 'node:test';
import assert from 'node:assert/strict';
import { ActionType, SUPPORTED_PROTOCOL_VERSIONS } from '@microsoft/agent-host-protocol';
import { AhpClient, AhpStateMirror, InMemoryTransport, RpcError } from '@microsoft/agent-host-protocol/client';
const ROOT='ahp-root://', SESSION='ahp-session:/watch-fixture';
async function request(peer) { const frame=await peer.recv(); assert.equal(frame.kind,'text'); return JSON.parse(frame.text); }
test('published SDK negotiates an advertised baseline', async()=>{
 const [c,s]=InMemoryTransport.pair(); const client=new AhpClient(c); client.connect();
 try {
  const pending=client.initialize({clientId:'watch-fixture',protocolVersions:[...SUPPORTED_PROTOCOL_VERSIONS],initialSubscriptions:[ROOT]});
  const req=await request(s); assert.equal(req.method,'initialize'); assert.ok(req.params.protocolVersions.includes('1.0.0'));
  s.send({jsonrpc:'2.0',id:req.id,result:{channel:ROOT,protocolVersion:'1.0.0',snapshots:[]}});
  assert.equal((await pending).protocolVersion,'1.0.0');
 } finally { await client.shutdown(); }
});
test('SDK exposes unsupported-version rejection without swallowing the error', async()=>{
 const [c,s]=InMemoryTransport.pair(); const client=new AhpClient(c); client.connect();
 try {
  const pending=client.initialize({clientId:'watch-fixture',protocolVersions:['999.0.0'],initialSubscriptions:[ROOT]});
  const rejection=assert.rejects(pending,e=>e instanceof RpcError && e.code===-32005);
  const req=await request(s); s.send({jsonrpc:'2.0',id:req.id,error:{code:-32005,message:'Unsupported protocol',data:{supportedVersions:['1.0.0']}}});
  await rejection;
 } finally { await client.shutdown(); }
});
test('two UI mirrors converge after ordered replay and ignore rejected actions',()=>{
 const desktop=new AhpStateMirror(), mobile=new AhpStateMirror();
 const snapshot={resource:SESSION,state:{provider:'fixture',title:'Before',status:'idle',lifecycle:'ready',activeClients:[],chats:[]},fromSeq:0};
 for(const mirror of [desktop,mobile]) mirror.applySnapshot(structuredClone(snapshot));
 const first={channel:SESSION,serverSeq:1,origin:null,action:{type:ActionType.SessionTitleChanged,title:'Shared'}};
 for(const mirror of [desktop,mobile]) mirror.apply(first);
 const replay={channel:SESSION,serverSeq:2,origin:null,action:{type:ActionType.SessionTitleChanged,title:'After reconnect'}};
 desktop.apply(replay); assert.notEqual(desktop.getSession(SESSION).title,mobile.getSession(SESSION).title);
 mobile.apply(replay); assert.deepEqual(desktop.getSession(SESSION),mobile.getSession(SESSION));
 for(const mirror of [desktop,mobile]) mirror.apply({channel:SESSION,serverSeq:3,origin:null,rejectionReason:'fixture denial',action:{type:ActionType.SessionTitleChanged,title:'Rejected'}});
 assert.equal(mobile.getSession(SESSION).title,'After reconnect');
 assert.deepEqual(desktop.getSession(SESSION),mobile.getSession(SESSION));
});
