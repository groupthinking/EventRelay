// Node 24+; dependency-free fixtures execute production TypeScript.
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';
let answers = [{ address: '93.184.216.34', family: 4 }];
let dnsError = false;
globalThis.__lookupFixture = async () => { if (dnsError) throw new Error('EAI_AGAIN'); return answers; };
registerHooks({
  resolve(specifier, context, next) {
    if (specifier === 'server-only') return { url: 'data:text/javascript,export default {};', shortCircuit: true };
    if (specifier === '@/lib/ssrf-guard') return { url: new URL('../../apps/web/src/lib/ssrf-guard.ts', import.meta.url).href, shortCircuit: true };
    if (specifier === 'node:dns/promises') return { url: 'data:text/javascript,export const lookup=(...a)=>globalThis.__lookupFixture(...a);', shortCircuit: true };
    return next(specifier, context);
  }
});
const { probeLiveDeploymentUrl: probe } = await import('../../apps/web/src/lib/live-deployment-probe.ts');
let calls = [];
let response = { status: 200, url: 'https://demo.vercel.app/', redirected: false };
let fetchError = false;
globalThis.fetch = async (url, init) => { calls.push({url,init}); if(fetchError) throw new Error('private-error'); return response; };
let cases = 0;
const check = async (url, expected) => { calls=[]; assert.deepEqual(await probe(url), expected); cases++; };
await check('https://demo.vercel.app', {ok:true,statusCode:200,finalUrl:'https://demo.vercel.app/'});
assert.equal(calls[0].init.redirect, 'error');
for(const status of [301,302,303,307,308]) { response={status,url:'https://demo.vercel.app/'}; await check('https://demo.vercel.app',{ok:false,statusCode:status,error:'redirect_rejected'});assert.equal(calls.length,1);assert.equal(calls[0].init.redirect,'error'); }
for(const url of ['http://127.0.0.1/admin','https://other.example/','https://demo.vercel.app/other']) { response={status:200,url};await check('https://demo.vercel.app',{ok:false,error:'target_mismatch'}); }
response={status:200,url:'https://demo.vercel.app/',redirected:true};await check('https://demo.vercel.app',{ok:false,error:'target_mismatch'});
for(const url of ['http://example.com/','https://user:secret@example.com/','https://localhost/','https://127.0.0.1/','https://[::1]/','https://example.com/#fragment']) {await check(url,{ok:false,error:'invalid_target'});assert.equal(calls.length,0);}
answers=[{address:'93.184.216.34',family:4},{address:'10.0.0.2',family:4}]; const err=console.error;console.error=()=>{};
await check('https://demo.vercel.app',{ok:false,error:'invalid_target'});assert.equal(calls.length,0);
dnsError=true;await check('https://demo.vercel.app',{ok:false,error:'invalid_target'});assert.equal(calls.length,0);dnsError=false;answers=[{address:'93.184.216.34',family:4}];console.error=err;
fetchError=true;await check('https://demo.vercel.app',{ok:false,error:'probe_failed'});assert.equal(calls.length,1);fetchError=false;
response={status:503,url:'https://demo.vercel.app/'};await check('https://demo.vercel.app',{ok:false,statusCode:503,error:'http_503'});assert.equal(calls.length,1);
await check('',{ok:false,error:'empty_url'});assert.equal(calls.length,0);
await check('https://example.com/'+'a'.repeat(2048),{ok:false,error:'invalid_target'});assert.equal(calls.length,0);
console.log(JSON.stringify({passed:cases,networkRequests:0,realDnsRequests:0,source:'unchanged TypeScript with import hooks only',scope:'fixture regression, not live network containment'}));
