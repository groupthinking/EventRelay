// Local transport experiment only: this fixture host is not a production AHP host.
import net from 'node:net';
import { once } from 'node:events';
import test from 'node:test';
import assert from 'node:assert/strict';
import { ActionType, SUPPORTED_PROTOCOL_VERSIONS } from '@microsoft/agent-host-protocol';
import { AhpClient, AhpStateMirror } from '@microsoft/agent-host-protocol/client';
const ROOT='ahp-root://', SESSION='ahp-session:/socket-fixture';
class Lines {
 constructor(socket) {
  this.socket=socket;this.queue=[];this.waiter=null;this.ended=false;let buffer='';
  socket.setEncoding('utf8');
  socket.on('data',text=>{buffer+=text;let at;while((at=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,at);buffer=buffer.slice(at+1);if(line)this.deliver({kind:'text',text:line});}});
  socket.on('end',()=>this.finish());socket.on('close',()=>this.finish());socket.on('error',()=>this.finish());
 }
 deliver(frame){if(this.waiter){const w=this.waiter;this.waiter=null;w(frame);}else this.queue.push(frame);}
 finish(){if(!this.ended){this.ended=true;this.deliver(null);}}
 recv(){if(this.queue.length)return Promise.resolve(this.queue.shift());if(this.ended)return Promise.resolve(null);return new Promise(r=>this.waiter=r);}
 send(message){this.socket.write((typeof message==='string'?message:JSON.stringify(message))+'\n');}
 close(){this.socket.destroy();this.finish();}
}
const bounded=p=>Promise.race([p,new Promise((_,reject)=>{const timer=setTimeout(()=>reject(new Error('fixture timeout')),3000);timer.unref();})]);
test('two real TCP clients receive actions, reconnect/replay, and preserve rejected state',{timeout:10000},async()=>{
 const sockets=new Set(),history=[],trace=[];let seq=0,title='Before';
 const snapshot=()=>({resource:SESSION,state:{provider:'fixture',title,status:'idle',lifecycle:'ready',activeClients:[],chats:[]},fromSeq:seq});
 const server=net.createServer(socket=>{
  sockets.add(socket);socket.on('close',()=>sockets.delete(socket));
  const peer=new Lines(socket);let clientId='uninitialized';
  void(async()=>{for(;;){const f=await peer.recv();if(!f)return;const m=JSON.parse(f.text);trace.push({method:m.method,clientId});
   const respond=result=>peer.send({jsonrpc:'2.0',id:m.id,result});
   if(m.method==='initialize'){clientId=m.params.clientId;assert.ok(m.params.protocolVersions.includes('1.0.0'));respond({channel:ROOT,protocolVersion:'1.0.0',snapshots:[]});}
   else if(m.method==='subscribe')respond({channel:SESSION,snapshot:snapshot()});
   else if(m.method==='reconnect'){clientId=m.params.clientId;respond({type:'replay',actions:history.filter(e=>e.serverSeq>m.params.lastSeenServerSeq),missing:[]});}
   else if(m.method==='dispatchAction'){
    const rejected=m.params.action.title==='Forbidden';const e={channel:SESSION,serverSeq:++seq,origin:{clientId,clientSeq:m.params.clientSeq},action:m.params.action,...(rejected?{rejectionReason:'fixture denied'}:{})};
    if(!rejected)title=e.action.title;history.push(e);
    for(const s of sockets)if(!s.destroyed)s.write(JSON.stringify({jsonrpc:'2.0',method:'action',params:e})+'\n');
   } else if(m.id!==undefined)peer.send({jsonrpc:'2.0',id:m.id,error:{code:-32601,message:'fixture method unsupported'}});
  }})().catch(error=>{server.fixtureError=error;socket.destroy();});
 });
 server.listen(0,'127.0.0.1');await once(server,'listening');const clients=[];
 async function connect(id,mirror,resume){
  const socket=net.createConnection(server.address().port,'127.0.0.1');await once(socket,'connect');
  const client=new AhpClient(new Lines(socket),{requestTimeoutMs:2000});clients.push(client);client.connect();
  if(resume!==undefined){const result=await client.reconnect({clientId:id,lastSeenServerSeq:resume,subscriptions:[SESSION]});assert.equal(result.type,'replay');assert.equal(result.actions.length,1);for(const e of result.actions)mirror.apply(e);assert.equal(mirror.getSession(SESSION).title,'Offline update');}
  else {await client.initialize({clientId:id,protocolVersions:[...SUPPORTED_PROTOCOL_VERSIONS],initialSubscriptions:[]});}
  const sub=await client.subscribe(SESSION);mirror.applySnapshot(sub.result.snapshot);return {client,sub:sub.subscription};
 }
 try {
  const desktopState=new AhpStateMirror(),mobileState=new AhpStateMirror();
  const desktop=await connect('desktop',desktopState),mobile=await connect('mobile',mobileState);
  desktop.client.dispatch(SESSION,{type:ActionType.SessionTitleChanged,title:'Shared'});
  for(const [c,m] of [[desktop,desktopState],[mobile,mobileState]])m.apply((await bounded(c.sub.next())).value.params);
  assert.deepEqual(desktopState.getSession(SESSION),mobileState.getSession(SESSION));
  await mobile.client.shutdown();
  desktop.client.dispatch(SESSION,{type:ActionType.SessionTitleChanged,title:'Offline update'});
  desktopState.apply((await bounded(desktop.sub.next())).value.params);
  assert.equal(mobileState.getSession(SESSION).title,'Shared');
  const resumed=await connect('mobile',mobileState,1);
  assert.equal(mobileState.getSession(SESSION).title,'Offline update');
  assert.deepEqual(desktopState.getSession(SESSION),mobileState.getSession(SESSION));
  desktop.client.dispatch(SESSION,{type:ActionType.SessionTitleChanged,title:'Forbidden'});
  for(const [c,m] of [[desktop,desktopState],[resumed,mobileState]]){const e=(await bounded(c.sub.next())).value.params;assert.equal(e.rejectionReason,'fixture denied');m.apply(e);}
  assert.equal(mobileState.getSession(SESSION).title,'Offline update');
  assert.deepEqual(desktopState.getSession(SESSION),mobileState.getSession(SESSION));
  assert.equal(server.fixtureError,undefined);
  console.log(JSON.stringify({transport:'TCP loopback',sdk:'1.1.0',negotiated:'1.0.0',connections:3,replay_actions:1,rejected_actions:1,methods:trace.map(t=>t.method),provider_calls:0,scope:'Synthetic local host; no production host/mobile/auth/persistence acceptance'}));
 } finally {for(const client of clients)await client.shutdown();for(const s of sockets)s.destroy();await new Promise(r=>server.close(r));}
});
